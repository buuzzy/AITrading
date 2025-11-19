import os
from dotenv import load_dotenv
import re
import argparse
import pandas as pd
import tinyshare as ts
from datetime import datetime
from typing import Optional, Tuple

import plotly.graph_objects as go

# 用于 backtest.py，将回测结果可视化
# 立即加载 .env，确保 TINYSHARE_TOKEN 在首次请求前可用
load_dotenv()


def normalize_symbol(sym: str) -> Tuple[str, str]:
    s = str(sym or '').strip().upper()
    if not s:
        return '', 'SZ'
    if '.' in s:
        base, exch = s.split('.', 1)
        base = base.strip().zfill(6)
        exch = exch.strip().upper()
        if exch in ('SSE', 'SH'):
            exch = 'SH'
        elif exch in ('SZSE', 'SZ'):
            exch = 'SZ'
        else:
            exch = 'SZ'
        return base, exch
    base = s.zfill(6)
    if base.startswith(('600', '601', '603', '605', '688')):
        exch = 'SH'
    elif base.startswith(('000', '001', '002', '003', '300')):
        exch = 'SZ'
    else:
        exch = 'SH' if base[0] == '6' else 'SZ'
    return base, exch


def parse_trades_filename(path: str) -> Optional[Tuple[str, str, str]]:
    """解析交易文件路径，返回 (symbol, start, end)。
    支持两种命名方案：
    1) 平铺：trades_<symbol>_<start>_<end>.csv
    2) 分票目录：backtest/<symbol>/trades_<start>_<end>.csv（symbol 从父目录名推断）
    """
    fname = os.path.basename(path)
    # 方案1：文件名自带 symbol
    m = re.match(r"trades_(\w+)_(\d{8})_(\d{8})\.csv", fname)
    if m:
        return m.group(1), m.group(2), m.group(3)
    # 方案2：文件名只有起止日期，从父目录名推断 symbol
    m2 = re.match(r"trades_(\d{8})_(\d{8})\.csv", fname)
    if not m2:
        return None
    parent = os.path.basename(os.path.dirname(path))
    sym = str(parent).strip()
    # 父目录应是6位股票代码（兼容可能的交易所后缀）
    if '.' in sym:
        sym = sym.split('.', 1)[0]
    if not re.match(r"^\d{6}$", sym):
        return None
    return sym, m2.group(1), m2.group(2)


def load_daily_ohlc(ts_code: str, start: str, end: str) -> pd.DataFrame:
    token = os.getenv('TINYSHARE_TOKEN')
    if token:
        try:
            ts.set_token(token)
            pro = ts.pro_api()
            print(f"[INFO] 使用 TINYSHARE_TOKEN 获取 {ts_code} {start}~{end} 日线数据（优先 daily）")
            df = pro.daily(ts_code=ts_code, start_date=start, end_date=end)
            if df is not None and not df.empty:
                df['trade_date'] = pd.to_datetime(df['trade_date'].astype(str), format='%Y%m%d')
                keep_cols = ['trade_date', 'open', 'high', 'low', 'close']
                df = df[keep_cols].copy()
                df = df.sort_values('trade_date').reset_index(drop=True)
                return df
            # 如果 daily 无数据，尝试 stk_factor 提取 OHLC（文档在 markdown/stk_factor.md）
            print(f"[WARN] daily 无数据，尝试 stk_factor 回退 {ts_code}")
            df2 = pro.stk_factor(ts_code=ts_code, start_date=start, end_date=end,
                                 fields='ts_code,trade_date,open,high,low,close')
            if df2 is not None and not df2.empty:
                df2['trade_date'] = pd.to_datetime(df2['trade_date'].astype(str), format='%Y%m%d')
                keep_cols = ['trade_date', 'open', 'high', 'low', 'close']
                df2 = df2[keep_cols].copy()
                df2 = df2.sort_values('trade_date').reset_index(drop=True)
                return df2
        except Exception:
            # 忽略在线失败，继续尝试本地回退
            pass

    # 次级回退：尝试兼容接口 get_k_data（无需 token），按日期范围拉取
    if not token:
        print(f"[WARN] 未检测到 TINYSHARE_TOKEN，尝试无 token 兼容接口 get_k_data 回退 {ts_code}")
    try:
        base = ts_code.split('.')[0]
        start_dash = f"{start[0:4]}-{start[4:6]}-{start[6:8]}"
        end_dash = f"{end[0:4]}-{end[4:6]}-{end[6:8]}"
        df_k = ts.get_k_data(base, start=start_dash, end=end_dash)
        if df_k is not None and not df_k.empty:
            # 统一列名
            if 'date' in df_k.columns:
                df_k['trade_date'] = pd.to_datetime(df_k['date'])
            else:
                # 某些实现可能返回 trade_date 数字
                df_k['trade_date'] = pd.to_datetime(df_k['trade_date'].astype(str), format='%Y%m%d')
            keep_cols = ['trade_date', 'open', 'high', 'low', 'close']
            df_k = df_k[[c for c in keep_cols if c in df_k.columns]].copy()
            df_k = df_k.sort_values('trade_date').reset_index(drop=True)
            return df_k
    except Exception:
        # 继续尝试本地缓存
        pass

    # 回退：尝试本地缓存的 *_factor.csv（若包含 OHLC 列）
    candidate = None
    if os.path.isdir('data'):
        for fname in os.listdir('data'):
            if fname.startswith(ts_code) and fname.endswith('_factor.csv'):
                candidate = os.path.join('data', fname)
                break
    if not candidate:
        raise RuntimeError('无法获取日线数据：未设置 token 的在线 daily 失败，且未找到本地缓存')
    df = pd.read_csv(candidate)
    # 统一字段名
    if 'trade_date' in df.columns:
        df['trade_date'] = pd.to_datetime(df['trade_date'].astype(str).str.replace('-', '', regex=False), format='%Y%m%d')
    elif 'date' in df.columns:
        df['trade_date'] = pd.to_datetime(df['date'])
    # 只保留需要的列
    keep_cols = ['trade_date', 'open', 'high', 'low', 'close']
    df = df[[c for c in keep_cols if c in df.columns]].copy()
    df = df[(df['trade_date'] >= pd.to_datetime(start)) & (df['trade_date'] <= pd.to_datetime(end))]
    df = df.sort_values('trade_date').reset_index(drop=True)
    return df


def load_trades(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # 兼容：date 可能为 YYYY-MM-DD
    df['date'] = pd.to_datetime(df['date'])
    # 仅保留成功的买/卖/平仓动作
    df = df[df['success'] == 1]
    df = df[df['signal'].isin(['buy', 'sell', 'close'])].copy()
    # 标注价格优先使用 effective_price（实际成交价，含滑点）；不存在则回退到 price
    if 'effective_price' in df.columns:
        df['marker_price'] = df['effective_price']
    else:
        df['marker_price'] = df['price']
    return df[['date', 'price', 'marker_price', 'signal', 'quantity']].sort_values('date').reset_index(drop=True)


def make_kline_with_signals(ohlc: pd.DataFrame, trades: pd.DataFrame, title: str):
    fig = go.Figure(
        data=[go.Candlestick(
            x=ohlc['trade_date'],
            open=ohlc['open'],
            high=ohlc['high'],
            low=ohlc['low'],
            close=ohlc['close'],
            name='K线'
        )]
    )

    # 标注买卖点：优先使用 marker_price（effective_price 回退到 price）
    if not trades.empty:
        # buy
        buys = trades[trades['signal'] == 'buy']
        sells = trades[trades['signal'] == 'sell']
        closes = trades[trades['signal'] == 'close']
        if not buys.empty:
            fig.add_trace(go.Scatter(
                x=buys['date'], y=buys['marker_price'],
                mode='markers+text',
                name='BUY',
                marker=dict(color='green', size=10, symbol='triangle-up'),
                text=[f"B {int(q)}" for q in buys['quantity']],
                textposition='top center'
            ))
        if not sells.empty:
            fig.add_trace(go.Scatter(
                x=sells['date'], y=sells['marker_price'],
                mode='markers+text',
                name='SELL',
                marker=dict(color='orange', size=10, symbol='triangle-down'),
                text=[f"S {int(q)}" for q in sells['quantity']],
                textposition='bottom center'
            ))
        if not closes.empty:
            fig.add_trace(go.Scatter(
                x=closes['date'], y=closes['marker_price'],
                mode='markers+text',
                name='CLOSE',
                marker=dict(color='red', size=11, symbol='x'),
                text=[f"C {int(q)}" for q in closes['quantity']],
                textposition='middle right'
            ))

    fig.update_layout(
        title=title,
        xaxis_title='日期',
        yaxis_title='价格',
        xaxis_rangeslider_visible=False,
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    return fig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trades', help='交易文件路径：trades_<symbol>_<start>_<end>.csv 或 backtest/<symbol>/trades_<start>_<end>.csv')
    parser.add_argument('--symbol', help='股票代码（如 600519 或 600519.SH）')
    parser.add_argument('--start', help='开始日期 YYYYMMDD')
    parser.add_argument('--end', help='结束日期 YYYYMMDD')
    parser.add_argument('--output', help='输出 HTML 文件路径（默认写入 specs/backtest/<symbol>/kline_<start>_<end>.html）', default=None)
    parser.add_argument('--output-root', help='输出根目录（默认 specs/backtest）', default=os.getenv('BACKTEST_OUTPUT_ROOT', 'specs/backtest'))
    args = parser.parse_args()

    if args.trades:
        info = parse_trades_filename(args.trades)
        if not info:
            raise SystemExit('trades 文件名不符合约定：trades_<symbol>_<start>_<end>.csv')
        symbol, start, end = info
    else:
        if not (args.symbol and args.start and args.end):
            raise SystemExit('缺少参数：请提供 --trades 或（--symbol, --start, --end）')
        symbol, start, end = args.symbol, args.start, args.end

    base, exch = normalize_symbol(symbol)
    ts_code = f"{base}.{exch}"

    ohlc = load_daily_ohlc(ts_code, start, end)
    trades_df = load_trades(args.trades) if args.trades else pd.DataFrame(columns=['date', 'price', 'signal', 'quantity'])

    title = f"{ts_code} {start}~{end} K线（含买卖点）"
    fig = make_kline_with_signals(ohlc, trades_df, title)

    # 统一默认输出到 backtest/<symbol>/kline_<start>_<end>.html
    if args.output:
        out = args.output
    else:
        symbol_dir = os.path.join(args.output_root, base)
        try:
            os.makedirs(symbol_dir, exist_ok=True)
        except Exception:
            pass
        out = os.path.join(symbol_dir, f"kline_{start}_{end}.html")
    fig.write_html(out, include_plotlyjs='cdn')
    print(f"已生成：{out}")


if __name__ == '__main__':
    main()