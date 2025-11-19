"""
最小回测脚手架：单标的、日线数据、LLM 决策、组合执行

用法：
  python backtest.py --symbol 600519 --start 20240101 --end 20241231
  python specs/demo/backtest.py --stocklist stocklist.csv --model deepseek-reasoner

说明：
- 历史数据来源：tinyshare（仅使用在线 pro.stk_factor，失败直接报错退出，不再回退本地缓存）
- 环境变量：需要 `.env` 中存在 `DEEPSEEK_API_KEY` 与 `TINYSHARE_TOKEN`
- 决策引擎：DeepSeek（OpenAI SDK，base_url 指向 deepseek），连续失败3次后暂停并等待用户确认继续或退出
"""
import os
import tinyshare as ts
import sys
import json
import math
import argparse
import logging
from typing import Dict, Any, List
import time
import uuid
import requests

import pandas as pd
import numpy as np
from dotenv import load_dotenv

load_dotenv()

from simple_portfolio import SimplePortfolio
# 导入：确保引入 build_market_prompt（你已有该行，保持不变）
from trade_decision_simple_AI import (
    trade_decision_provider as ai_trade_decision_provider,
    market_data_to_string_for_symbol,
    portfolio_to_string,
    SYSTEM_PROMPT_TEXT,
    build_market_prompt,
    compute_strategy_flags,
)
# 引入 Dify 技术分析请求（优先 py_trader.live_trader，其次 livetrade）
try:
    from py_trader.live_trader import request_technical_analysis as request_technical_analysis_dify
except Exception:
    try:
        from livetrade import request_technical_analysis as request_technical_analysis_dify
    except Exception:
        def request_technical_analysis_dify(symbol: str, ts_code: str, today: str, prev_open: str):
            return None

# 辅助：读写 JSON（进度与 LLM 输出），以及 CSV 按日期唯一覆盖
def _load_json(path: str) -> Dict[str, Any]:
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def _save_json(path: str, obj: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
    except Exception:
        print(f"⚠️ 写入 JSON 失败：{path}")

def _upsert_trades_csv(path: str, header: str, date_key: str, line: str) -> None:
    # 读取已存在内容；删除同日期旧行；写回（保留表头）
    rows: List[str] = []
    try:
        if os.path.isfile(path):
            with open(path, 'r', encoding='utf-8') as f:
                rows = f.read().splitlines()
    except Exception:
        rows = []
    # 保证表头
    new_rows: List[str] = [header]
    for r in rows[1:] if rows else []:
        try:
            d = r.split(',')[0].strip()
        except Exception:
            d = ''
        if d and d != date_key:
            new_rows.append(r)
    new_rows.append(line)
    # 按日期排序（YYYY-MM-DD 字符串可直接排序）
    try:
        body = new_rows[1:]
        body_sorted = sorted(body, key=lambda s: s.split(',')[0])
        new_rows = [header] + body_sorted
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_rows) + "\n")
    except Exception:
        print(f"⚠️ 写入交易 CSV 失败：{path}")

def normalize_symbol(sym: str):
    """规范化A股代码并推断交易所。
    返回 (base_code, exchange) 其中 base_code 为6位代码（保留前导零），exchange 为 'SH' 或 'SZ'。
    规则：
    - 若带后缀（如 600519.SH / 000001.SZ），保留后缀并将代码补齐至6位。
    - 若不带后缀：
      * 以 '600','601','603','605','688' 开头归为上交所 SH；
      * 以 '000','001','002','003','300' 开头归为深交所 SZ；
      * 兜底：首位为 '6' 归 SH，否则归 SZ。
    """
    s = str(sym or '').strip().upper()
    if not s:
        return '', 'SZ'
    if '.' in s:
        base, exch = s.split('.', 1)
        base = base.strip().zfill(6)
        exch = exch.strip().upper()
        if exch in ('SSE', 'SH'): exch = 'SH'
        elif exch in ('SZSE', 'SZ'): exch = 'SZ'
        else: exch = 'SZ'
        return base, exch
    base = s.zfill(6)
    if base.startswith(('600', '601', '603', '605', '688')):
        exch = 'SH'
    elif base.startswith(('000', '001', '002', '003', '300')):
        exch = 'SZ'
    else:
        exch = 'SH' if base[0] == '6' else 'SZ'
    return base, exch


def compute_ema(series: pd.Series, span: int = 20) -> pd.Series:
    try:
        return series.ewm(span=span, adjust=False).mean()
    except Exception:
        return pd.Series([None] * len(series))

# === Supabase 自动入库辅助 ===
def _supabase_creds():
    url = (
        os.getenv('SUPABASE_URL')
        or os.getenv('AITRADE_SUPABASE_URL')
        or os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    )
    key = (
        os.getenv('SUPABASE_KEY')
        or os.getenv('AITRADE_SUPABASE_KEY')
        or os.getenv('NEXT_PUBLIC_SUPABASE_KEY')
    )
    return url, key

def _supabase_headers(key: str, prefer_merge: bool = True):
    h = {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
    }
    if prefer_merge:
        h['Prefer'] = 'resolution=merge-duplicates'
    return h

def _supabase_upsert(table: str, rows: List[Dict[str, Any]], on_conflict: str = None):
    url, key = _supabase_creds()
    if not url or not key:
        return False, 'missing_supabase_env'
    endpoint = f"{url}/rest/v1/{table}"
    params = {}
    if on_conflict:
        params['on_conflict'] = on_conflict
    try:
        r = requests.post(endpoint, headers=_supabase_headers(key, True), params=params, data=json.dumps(rows), timeout=30)
        if 200 <= r.status_code < 300:
            return True, None
        try:
            err = r.json()
        except Exception:
            err = r.text
        return False, err
    except Exception as e:
        return False, str(e)

def _ensure_run(symbol: str, start_date: str, end_date: str, label: str = None) -> str:
    url, key = _supabase_creds()
    if not url or not key:
        return str(uuid.uuid4())
    base_sym, _exch = normalize_symbol(symbol)
    if not label:
        label = f"{base_sym}_{start_date}_{end_date}"
    # 先查询是否已有同 label 的 run
    try:
        g = requests.get(
            f"{url}/rest/v1/runs",
            headers=_supabase_headers(key, False),
            params={'select': 'run_id', 'label': f"eq.{label}"},
            timeout=15
        )
        if g.status_code == 200:
            arr = g.json()
            if isinstance(arr, list) and arr:
                rid = arr[0].get('run_id')
                if rid:
                    return rid
    except Exception:
        pass
    # 创建新的 run 记录
    run_id = str(uuid.uuid4())
    payload = [{
        'run_id': run_id,
        'label': label,
        'status': 'running',
        'start_date': start_date,
        'end_date': end_date,
        'created_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    }]
    ok, err = _supabase_upsert('runs', payload, on_conflict='run_id')
    if not ok:
        print(f"⚠️ 创建 runs 记录失败（忽略，仅本地写文件）：{err}")
    return run_id

def _supabase_upsert_trade(run_id: str, symbol: str, date_str: str, row: Dict[str, Any]):
    base_sym, _ = normalize_symbol(symbol)
    sig = str(row.get('signal') or '').lower()
    # trades.side 仅允许 buy/sell/hold；close 映射为 sell
    side = 'buy' if sig == 'buy' else ('sell' if sig in ('sell', 'close') else 'hold')
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        # 支持两种输入格式：YYYYMMDD 或 YYYY-MM-DD，统一存为 ISO 日期
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'side': side,
        'qty': float(row.get('quantity')) if row.get('quantity') is not None else None,
        'price': float(row.get('price')) if row.get('price') is not None else None,
        'effective_price': float(row.get('effective_price')) if row.get('effective_price') is not None else None,
        'cash_before': float(row.get('cash_before')) if row.get('cash_before') is not None else None,
        'cash_after': float(row.get('cash_after')) if row.get('cash_after') is not None else None,
        'position_before': float(row.get('position_before')) if row.get('position_before') is not None else None,
        'position_after': float(row.get('position_after')) if row.get('position_after') is not None else None,
        'pnl': float(row.get('pnl')) if row.get('pnl') is not None else None,
        'note': str(row.get('note')) if row.get('note') is not None else None,
    }
    return _supabase_upsert('trades', [doc], on_conflict='run_id,symbol,date')

def _supabase_upsert_daily_metrics(run_id: str, symbol: str, date_str: str, cash: float, equity: float, position: float, initial_cash: float = None, daily_return: float = None):
    base_sym, _ = normalize_symbol(symbol)
    nav_val = None
    try:
        if initial_cash and initial_cash > 0:
            nav_val = float(equity) / float(initial_cash)
    except Exception:
        nav_val = None
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        # 支持两种输入格式：YYYYMMDD 或 YYYY-MM-DD，统一存为 ISO 日期
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'nav': nav_val,
        'cash': float(cash) if cash is not None else None,
        'position': float(position) if position is not None else None,
        'daily_return': float(daily_return) if daily_return is not None else None,
        'equity': float(equity) if equity is not None else None,
    }
    return _supabase_upsert('daily_metrics', [doc], on_conflict='run_id,symbol,date')

def _supabase_upsert_ohlc(run_id: str, symbol: str, date_str: str, open_p: float, high_p: float, low_p: float, close_p: float, source: str = 'tinyshare'):
    base_sym, _ = normalize_symbol(symbol)
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'open': float(open_p) if open_p is not None else None,
        'high': float(high_p) if high_p is not None else None,
        'low': float(low_p) if low_p is not None else None,
        'close': float(close_p) if close_p is not None else None,
        'source': source,
    }
    return _supabase_upsert('ohlc', [doc], on_conflict='symbol,date')

# === Cloudflare R2 上传辅助（S3 兼容） ===
def _r2_client():
    endpoint = os.getenv('R2_ENDPOINT_URL')
    access_key = os.getenv('R2_ACCESS_KEY_ID')
    secret_key = os.getenv('R2_SECRET_ACCESS_KEY')
    bucket = os.getenv('R2_BUCKET_NAME') or os.getenv('STORAGE_BUCKET')
    if not endpoint or not access_key or not secret_key or not bucket:
        return None, 'missing_r2_env'
    try:
        import boto3
        s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name='auto'
        )
        return (s3, bucket), None
    except Exception as e:
        return None, str(e)

def _r2_upload(local_path: str, key_prefix: str, run_id: str, symbol: str, start_date: str, end_date: str):
    client_bucket, err = _r2_client()
    if not client_bucket:
        return False, err
    s3, bucket = client_bucket
    if not os.path.isfile(local_path):
        return False, f'file_not_found:{local_path}'
    filename = os.path.basename(local_path)
    key = f"{key_prefix}/{symbol}/{end_date}/{filename}"
    extra = {}
    if filename.endswith('.json'):
        extra['ContentType'] = 'application/json'
    elif filename.endswith('.ndjson'):
        extra['ContentType'] = 'application/x-ndjson'
    elif filename.endswith('.csv'):
        extra['ContentType'] = 'text/csv'
    try:
        s3.upload_file(local_path, bucket, key, ExtraArgs=extra)
        return True, None
    except Exception as e:
        return False, str(e)

# === Supabase 额外表：checkpoints 与 errors ===
def _supabase_upsert_checkpoint(run_id: str, symbol: str, date_str: str, reason: str):
    base_sym, _ = normalize_symbol(symbol)
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        # 支持两种输入格式：YYYYMMDD 或 YYYY-MM-DD，统一存为 ISO 日期
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'reason': str(reason),
    }
    return _supabase_upsert('checkpoints', [doc], on_conflict='run_id,symbol,date')

def _supabase_insert_error(run_id: str, symbol: str, date_str: str, source: str, code: str, message: str, raw: Dict[str, Any] = None):
    base_sym, _ = normalize_symbol(symbol)
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        # 支持两种输入格式：YYYYMMDD 或 YYYY-MM-DD，统一存为 ISO 日期
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'source': str(source or 'other'),
        'code': str(code or 'unknown'),
        'message': str(message or ''),
        'raw': raw if isinstance(raw, dict) else None,
    }
    # errors 使用自增 id/uuid 作为主键，直接插入即可
    return _supabase_upsert('errors', [doc])

def _supabase_update_run_status(run_id: str, status: str):
    payload = [{
        'run_id': run_id,
        'status': status,
        'finished_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'completed' else None,
    }]
    return _supabase_upsert('runs', payload, on_conflict='run_id')


def compute_macd(series: pd.Series, fast: int = 12, slow: int = 26) -> pd.Series:
    try:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        return ema_fast - ema_slow
    except Exception:
        return pd.Series([None] * len(series))

def compute_macd_full(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """标准 MACD 三元组：DIF、DEA、Histogram。
    - DIF = EMA(fast) - EMA(slow)
    - DEA = EMA(DIF, signal)
    - Hist = 2 * (DIF - DEA)
    返回三个同长度的 pd.Series（失败时以 None 填充）。
    """
    try:
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        dif = ema_fast - ema_slow
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = 2.0 * (dif - dea)
        return dif, dea, hist
    except Exception:
        n = len(series)
        none_series = pd.Series([None] * n)
        return none_series, none_series, none_series


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI（滚动均值版）。

    行为约定：
    - 样本不足 period 前返回 NaN（min_periods=period）。
    - 当平均损失为 0 时，RSI 设为 100（价格持续上涨的极端情况）。
    - 当平均收益为 0 且平均损失>0 时，RSI 设为 0（价格持续下跌的极端情况）。
    - 当平均收益与平均损失均为 0（完全平盘）时，RSI 设为 50。
    这样可避免将有效极端情形误处理为 N/A。
    """
    try:
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()

        rsi = pd.Series(index=series.index, dtype=float)
        ready = avg_gain.notna() & avg_loss.notna()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi.loc[ready] = 100.0 - (100.0 / (1.0 + rs.loc[ready]))

        # 极端情形修正（保持向量化）
        rsi.loc[(avg_loss == 0) & (avg_gain > 0)] = 100.0
        rsi.loc[(avg_gain == 0) & (avg_loss > 0)] = 0.0
        rsi.loc[(avg_gain == 0) & (avg_loss == 0)] = 50.0

        return rsi
    except Exception:
        # 返回同长度的 NaN 序列，让下游按缺失处理
        return pd.Series([np.nan] * len(series))


def build_market_data_for_day(symbol: str, closes: pd.Series, up_to_index: int) -> Dict[str, Any]:
    """基于收盘价序列构造 AI 决策所需的最小市场数据结构（1d）。"""
    # 固定近30日窗口，样本不足则使用已有的全部历史
    start_idx = max(0, up_to_index - 29)
    window = closes.iloc[start_idx: up_to_index + 1]
    # 严格的“前30日”窗口（不含当前日），样本不足则返回已有的历史（最多30）
    prev30_start_idx = max(0, up_to_index - 30)
    prev30 = closes.iloc[prev30_start_idx: up_to_index]
    recent_10 = window.iloc[max(0, len(window) - 10):]
    ema20 = compute_ema(window, 20)
    # MACD/RSI 使用数据源的 stk_factor（在上层注入 factor_* 字段）；本地仅保留 EMA(20)

    return {
        'frequency': '1d',
        'current_price': float(window.iloc[-1]),
        'current_close_20_ema': None if ema20.empty else float(ema20.iloc[-1]),
        # MACD/RSI 当前值与序列由上层注入的 factor_* 字段提供（对齐数据源）
        'open_interest_latest': None,
        'open_interest_average': None,
        'funding_rate': None,
        # 使用收盘价作为“mid_prices”的替代，以保持与现有下游字段兼容
        'mid_prices': [float(x) for x in window.tolist()],
        # 最近30个交易日的收盘价序列（严格为“当前日之前”，不含当日）
        'recent_30_closes': [float(x) for x in prev30.tolist()],
        # 最近10个交易日的收盘价序列（供 LLM 参考）
        'recent_10_closes': [float(x) for x in recent_10.tolist()],
        'ema_20_array': [None if (x is None or (isinstance(x, float) and math.isnan(x))) else float(x) for x in ema20.tolist()],
        # MACD/RSI 数组不在本地计算，显示改由 factor_series_* 提供
    }


def clamp_quantity_to_cash(quantity: float, price: float, leverage: float, available_cash: float) -> float:
    if leverage <= 0:
        leverage = 1.0
    max_affordable = (available_cash * leverage) / max(price, 1e-8)
    if abs(quantity) > max_affordable:
        quantity = math.copysign(max_affordable, quantity)
    return quantity

def apply_a_share_lot_rules(signal: str, quantity: float, price: float, available_cash: float, lot_size: int = 100, min_lot_count: int = 1) -> int:
    """A股规则：数量按手取整，最少1手；根据现金约束计算最大可买手数。

    返回：按股为单位的整数数量（shares）。若不可买，返回0。
    """
    if signal != 'buy':
        return 0 if signal in ('hold', 'close') else 0
    # 将模型给出的数量视作“股数”，下取整到lot倍数
    q_shares = int(max(0, quantity))
    if lot_size <= 0:
        lot_size = 100
    lots = q_shares // lot_size
    # 现金可支撑的最大手数
    max_lots_cash = int(available_cash // (price * lot_size))
    lots = min(lots, max_lots_cash)
    if lots < min_lot_count:
        return 0
    return lots * lot_size


def run_backtest(symbol: str, start_date: str, end_date: str,
                 hide_prompts: bool = False,
                 hide_reasoning: bool = False,
                 sleep_seconds: int = 60,
                 initial_cash: float = 100000.0,
                 lot_size: int = 100,
                 commission_rate: float = 0.0003,
                 stamp_duty_rate: float = 0.0005,
                 transfer_fee_rate: float = 0.00001,
                 model_name: str = "deepseek-chat",
                 llm_ndjson: bool = False,
                 strict_deps: bool = False) -> Dict[str, Any]:
    logger = logging.getLogger("backtest")
    # 默认采用“关键里程碑”日志风格：不打印完整 prompts/reasoning，仅输出关键节点
    # 保留 hide_prompts/hide_reasoning 兼容，但默认代码路径不再打印这些长文本
    # 统一规范化代码与交易所
    norm_symbol, exch = normalize_symbol(symbol)
    symbol = norm_symbol
    ts_code = f"{symbol}.{exch}"
    logger.info(f"开始最小回测：symbol={symbol}({exch}), start={start_date}, end={end_date}")
    # 交易所差异：沪市收取过户费，深市不收
    is_shanghai = (exch == 'SH')

    # 1) 优先在线：使用 tinyshare 的 stk_factor（包含OHLC+技术指标）对齐数据源
    token = os.getenv("TINYSHARE_TOKEN")
    if not token:
        logger.error("缺少 TINYSHARE_TOKEN，无法拉取在线因子数据。请在 .env 配置后重试。")
        return {}
    df = pd.DataFrame()
    try:
        ts.set_token(token)
        pro = ts.pro_api()
        # 已在上方规范化 ts_code
        # 在线拉取：为保证有“开始日前30个交易日”上下文，扩展开始日期向前约90天
        start_dt_safe = pd.to_datetime(start_date, errors='coerce')
        end_dt_safe = pd.to_datetime(end_date, errors='coerce')
        prefetch_start_dt = start_dt_safe - pd.Timedelta(days=90)
        prefetch_start_str = prefetch_start_dt.strftime('%Y%m%d')
        end_str = end_dt_safe.strftime('%Y%m%d')
        # 直接使用 stk_factor，避免本地再计算 MACD/RSI
        df = pro.stk_factor(ts_code=ts_code, start_date=prefetch_start_str, end_date=end_str)
        if not df.empty:
            df = df.rename(columns={'trade_date': 'date'})
            date_str = df['date'].astype(str).str.replace('-', '', regex=False).str.strip()
            df['date'] = pd.to_datetime(date_str, format='%Y%m%d', errors='coerce')
            # 过滤到 end_dt 之前，并拼接开始日前最多30个交易日历史
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            try:
                df = df[df['date'] <= end_dt].copy()
                df_main = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()
                if df_main.empty:
                    logger.error("在线因子数据过滤后为空，请调整日期范围")
                    return {}
                df_pre = df[df['date'] < start_dt].tail(30).copy()
                df = pd.concat([df_pre, df_main], ignore_index=True)
                df = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
                pre_len = len(df_pre)
                if pre_len < 1:
                    logger.warning("在线数据首日无前置历史（<30），首个窗口可能较短；建议扩大在线下载区间以提升首日决策上下文。")
            except Exception as e:
                logger.warning(f"在线数据拼接开始日前历史失败，回退为严格区间：{e}")
                df = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()
                if df.empty:
                    logger.error("在线因子数据过滤后为空，请调整日期范围")
                    return {}
        else:
            logger.error("stk_factor 返回为空，请检查 ts_code/日期范围。")
            return {}
    except Exception as e:
        logger.error(f"stk_factor 拉取失败：{e}")
        return {}

    # 标准化并按交易日排序
    if 'trade_date' in df.columns and 'date' not in df.columns:
        df['date'] = pd.to_datetime(df['trade_date'].astype(str))
    df = df.sort_values('date').reset_index(drop=True)

    # 收盘价转为数值类型，避免字符串或非数值导致计算异常（以 stk_factor 的 close 字段为准）
    if 'close' not in df.columns:
        logger.error("数据集中缺少 close 列（stk_factor），无法运行回测。")
        return {}
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    if df['close'].isna().all():
        logger.error("close 列全部不可用（NaN），请检查数据源或日期范围。")
        return {}
    closes = df['close']

    # 加载交易日历并过滤到 open 日（强制在线，不读本地缓存）
    start_str = start_date.replace('-', '')
    end_str = end_date.replace('-', '')
    try:
        exch_api = 'SSE' if is_shanghai else 'SZSE'
        cal_df = pro.trade_cal(exchange=exch_api, start_date=start_str, end_date=end_str)
        if cal_df is None or cal_df.empty:
            raise RuntimeError('在线交易日历为空')
        cal_df['cal_date'] = cal_df['cal_date'].astype(str).str.replace('-', '', regex=False).str.strip()
        cal_df['is_open'] = pd.to_numeric(cal_df['is_open'], errors='coerce').fillna(0).astype(int)
        open_days = sorted(cal_df.loc[cal_df['is_open'] == 1, 'cal_date'].tolist())
    except Exception as e:
        logger.warning(f"在线 trade_cal 获取失败或为空，回退使用数据集主区间日期：{e}")
        try:
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            df_main_only = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
            open_days = sorted(df_main_only['date'].dt.strftime('%Y%m%d').tolist())
        except Exception:
            open_days = sorted(df['date'].dt.strftime('%Y%m%d').tolist())
        if not open_days:
            logger.warning(f"交易日历不覆盖区间 {start_str}~{end_str}，回退使用数据集中日期作为交易日（仅主区间）。")
            try:
                # 使用主区间的 df 作为交易日列表来源，避免将前置历史作为迭代日
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df_main_only = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)]
                open_days = sorted(df_main_only['date'].dt.strftime('%Y%m%d').tolist())
            except Exception:
                open_days = sorted(df['date'].dt.strftime('%Y%m%d').tolist())

    # 建立交易日到行索引的映射
    df['date_str'] = df['date'].dt.strftime('%Y%m%d')
    idx_map = {row['date_str']: i for i, row in df.iterrows()}
    # 调试：打印交易日与数据日期范围，定位不匹配问题
    if open_days:
        print(f"交易日数量: {len(open_days)} | 首日: {open_days[0]} | 末日: {open_days[-1]}")
    if not df.empty:
        df_dates = df['date_str'].tolist()
        print(f"数据日期范围: {df_dates[0]} ~ {df_dates[-1]} | 记录数: {len(df_dates)}")

    # 统一输出目录到 specs/backtest/<symbol>/
    out_dir = os.path.join("specs", "backtest", symbol)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except Exception:
        # 若目录创建失败，仍尝试在根目录写入，但给出警告
        logger.warning(f"创建输出目录失败：{out_dir}，将回退写入项目根目录。")
        out_dir = "."
    # 稳定文件名：progress、LLM 决策 JSON、交易 CSV
    progress_json_path = os.path.join(out_dir, f"progress_{symbol}.json")
    llm_json_path = os.path.join(out_dir, f"llm_{symbol}.json")
    trades_csv_path = os.path.join(out_dir, f"trades_{symbol}.csv")
    llm_ndjson_path = os.path.join(out_dir, f"llm_returns_{symbol}_{start_date}_{end_date}.ndjson")
    portfolio_state_path = os.path.join(out_dir, 'portfolio_state.json')
    # 若交易 CSV 不存在则写入表头
    if not os.path.isfile(trades_csv_path):
        try:
            os.makedirs(out_dir, exist_ok=True)
            with open(trades_csv_path, 'w', encoding='utf-8') as fcsv:
                fcsv.write("date,price,signal,quantity,leverage,success,available_cash,total_asset,llm_ms,effective_price\n")
        except Exception:
            print(f"⚠️ 初始化交易 CSV 失败：{trades_csv_path}")
    # 组合初始化与输出头
    portfolio = SimplePortfolio(initial_cash=initial_cash)
    try:
        if os.path.isfile(portfolio_state_path):
            portfolio.load_from_file(portfolio_state_path)
    except Exception:
        pass
    print(f"模型: {model_name}")
    print(f"标的: {symbol} | 时间范围: {start_date} ~ {end_date}")
    print(f"初始资金: {portfolio.initial_cash:.2f}")
    print("开始回测（仅在交易日执行一次，价格=当日收盘价）")
    print("日期        收盘价     决策    数量         可用现金       总资产      LLM耗时(ms)")

    actions: List[Dict[str, Any]] = []
    llm_raw_records: List[Dict[str, Any]] = []
    # 建立/获取 run_id（用于云端记录的主键）
    run_id = _ensure_run(symbol, start_date, end_date)
    # 累计费用与交易统计
    total_commission: float = 0.0
    total_transfer: float = 0.0
    total_stamp: float = 0.0
    trades_total: int = 0
    trades_won: int = 0
    trades_lost: int = 0
    gross_profit_total: float = 0.0  # 不含费用的毛利润（按平仓时价差）
    gross_loss_total: float = 0.0    # 不含费用的毛亏损（绝对值累计）

    # T+1：记录可卖出日期
    can_sell_after: Dict[str, str] = {}

    # 载入进度：决定从何处继续
    progress_obj = _load_json(progress_json_path)
    last_processed = str(progress_obj.get('last_processed_date') or '').replace('-', '')
    start_str_effective = start_date.replace('-', '')
    # 仅处理 >= start 且 > last_processed 的日期（确保幂等覆盖）
    process_days = [d for d in open_days if d >= start_str_effective and (not last_processed or d > last_processed)]

    first_day_debug_done = False
    # 最小冷却状态机：探索买入或卖出/平仓后，3个开放日内禁止买入
    # 载入持久化状态
    try:
        if isinstance(progress_obj.get('can_sell_after'), dict):
            can_sell_after = {str(k): str(v) for k, v in progress_obj.get('can_sell_after').items()}
    except Exception:
        can_sell_after = {}
    try:
        buy_cooldown_until = progress_obj.get('buy_cooldown_until')
    except Exception:
        buy_cooldown_until = None
    buy_cooldown_until = str(buy_cooldown_until) if buy_cooldown_until else None
    for dstr in process_days:
        if dstr not in idx_map:
            # 若目标交易日在数据集中不存在，通常意味着已到数据末尾（例如当日尚无数据），停止并记录进度
            break
        i = idx_map[dstr]
        date_str = df.iloc[i]['date'].strftime('%Y-%m-%d')
        price = float(df.iloc[i]['close'])
        # 当日 OHLC（用于现实化成交价夹逼在最高/最低之间）
        day_open = float(df.iloc[i]['open']) if 'open' in df.columns and not pd.isna(df.iloc[i]['open']) else None
        day_high = float(df.iloc[i]['high']) if 'high' in df.columns and not pd.isna(df.iloc[i]['high']) else None
        day_low = float(df.iloc[i]['low']) if 'low' in df.columns and not pd.isna(df.iloc[i]['low']) else None

        # 采用近30个交易日窗口（首次必须提供上下文）
        start_idx = max(0, i - 30)  # 修正：最多31天窗口，保证 prev30 恰为30条
        window_closes = df['close'].iloc[start_idx:i+1]

        portfolio.update_price(symbol, price)

        # 用 30 日窗口构造市场数据
        md_one = build_market_data_for_day(symbol, window_closes, len(window_closes) - 1)
        # 传递 stk_factor 指标列（当前值与近窗序列）：MACD/RSI/KDJ/BOLL/CCI
        factor_cols = [
            'macd', 'macd_dif', 'macd_dea',
            'rsi_6', 'rsi_12', 'rsi_24',
            'kdj_k', 'kdj_d', 'kdj_j',
            'boll_upper', 'boll_mid', 'boll_lower',
            'cci'
        ]
        for col in factor_cols:
            if col in df.columns:
                try:
                    cur_val = df.iloc[i][col]
                    md_one[f'factor_{col}'] = None if pd.isna(cur_val) else float(cur_val)
                except Exception:
                    md_one[f'factor_{col}'] = None
                try:
                    series_window = df[col].iloc[start_idx:i+1].tolist()
                    md_one[f'factor_series_{col}'] = [None if (x is None or (isinstance(x, float) and math.isnan(x))) else float(x) for x in series_window]
                except Exception:
                    md_one[f'factor_series_{col}'] = []
        # 注入冷却状态（供 LLM 与本地门槛统一使用）
        in_cooldown = False
        try:
            if buy_cooldown_until and dstr < buy_cooldown_until:
                in_cooldown = True
        except Exception:
            in_cooldown = False
        md_one['buy_cooldown'] = bool(in_cooldown)

        md_dict = {symbol: md_one}
        pf_json = portfolio.return_json()

        # 注入可执行状态与规则供 LLM 使用
        has_position = symbol in portfolio.positions and portfolio.positions[symbol].quantity != 0
        # 简化：是否为首次交易（无任何历史 action）
        is_first_trade = (len(actions) == 0)
        last_action = actions[-1]['signal'] if actions else 'none'
        # T+1：今日是否可卖（若此前记录了 next 卖出日且今日>=该日）
        allowed_date = can_sell_after.get(symbol)
        tplus1_sell_available_today = bool(allowed_date and dstr >= allowed_date)
        # 当前持仓手数（用于 LLM 约束部分减仓）
        current_position_lots = 0
        avg_entry_price_for_symbol = None
        if has_position:
            try:
                current_qty_tmp = float(getattr(portfolio.positions[symbol], 'quantity', 0.0))
                current_position_lots = int(current_qty_tmp // lot_size)
                avg_entry_price_for_symbol = float(getattr(portfolio.positions[symbol], 'entry_price', None) or 0.0)
            except Exception:
                current_position_lots = 0
                avg_entry_price_for_symbol = None
        recent_actions_text = None
        try:
            filtered = [a for a in actions if str(a.get('signal')).lower() in ('buy', 'sell', 'close') and a.get('success')]
            last_k = filtered[-10:]
            if last_k:
                lines = []
                for a in last_k:
                    qty_lots = int(a.get('quantity') or 0) // lot_size
                    ep = a.get('effective_price', a.get('price'))
                    ep_str = (f"{float(ep):.2f}" if ep is not None else "N/A")
                    pnl_val = a.get('pnl', None)
                    pnl_str = (f"{float(pnl_val):.2f}" if isinstance(pnl_val, (int, float)) else "N/A")
                    lines.append(f"- {a.get('date')} | side={a.get('signal')} | qty={qty_lots}手 | price={ep_str} | pnl={pnl_str}")
                try:
                    idx_cur = open_days.index(dstr)
                except Exception:
                    idx_cur = None
                hold_days = None
                if idx_cur is not None:
                    try:
                        idx_start = open_days.index(start_date) if start_date in open_days else 0
                    except Exception:
                        idx_start = 0
                    window = open_days[idx_start: idx_cur + 1]
                    traded = set()
                    for a in last_k:
                        dd = a.get('date')
                        if dd:
                            traded.add(dd.replace('-', ''))
                    hold_days = len([d for d in window if d not in traded])
                if hold_days is not None:
                    lines.append(f"- 从最早日期至今，除以上交易日外均为 hold（{hold_days} 天）")
                recent_actions_text = "\n".join(lines)
        except Exception:
            recent_actions_text = None
        # 允许动作：有仓且满足T+1时，开放 sell（部分减仓）与 close（全平）
        allowed_actions = ['buy', 'hold'] if not has_position else (
            ['buy', 'hold', 'sell', 'close'] if tplus1_sell_available_today else ['buy', 'hold']
        )
        # 预扣买入费用（佣金 + 过户费）并加入买入滑点，提高买入成本，避免买入后现金因费用/滑点为负
        fees_rate = (commission_rate + (transfer_fee_rate if is_shanghai else 0.0))
        try:
            slippage_buy_pct = float(os.getenv('SLIPPAGE_BUY_PCT', '0.01'))  # 默认 1%
        except Exception:
            slippage_buy_pct = 0.01
        per_lot_total = price * (1.0 + slippage_buy_pct) * lot_size * (1.0 + fees_rate)
        max_buyable_lots = int(portfolio.available_cash // per_lot_total)
        md_one['llm_state'] = {
            'has_position': has_position,
            'is_first_trade': is_first_trade,
            'last_action': last_action,
            'allowed_actions': allowed_actions,
            'lot_size': lot_size,
            'min_lot_count': 1,
            'tplus1_sell_available_today': tplus1_sell_available_today,
            'available_cash': float(portfolio.available_cash),
            'current_price': float(price),
            'max_buyable_lots': max_buyable_lots,
            'max_sellable_lots': current_position_lots,
            'default_position_fraction': 0.25,
            'avg_entry_price': avg_entry_price_for_symbol,
            'recent_actions_text': recent_actions_text,
        }

        # Dify 技术分析：作为可选参考与审计说明注入；失败不中断
        idx_in_days = open_days.index(dstr)
        pre_open = open_days[idx_in_days - 1] if (idx_in_days - 1) >= 0 else None
        ta_text = None
        last_err = None
        attempts = 0
        while attempts < 3 and not ta_text:
            try:
                ta_text = request_technical_analysis_dify(symbol, ts_code, dstr, pre_open or '')
                if ta_text:
                    md_one['technical_analysis'] = ta_text
                    _frag = (ta_text or '')[:80].replace('\n', ' ').replace('"', '\"')
                    print(f"节点：Dify 返回 | technical_analysis 长度={len(ta_text or '')} 片段=\"{_frag}\"")
                    break
                else:
                    raise RuntimeError('empty_ta')
            except Exception as e:
                last_err = e
                attempts += 1
                if attempts < 3:
                    logger.warning(f"Dify 技术分析获取失败（第{attempts}次）：{e}，2 秒后重试…")
                    try:
                        time.sleep(2)
                    except Exception:
                        pass
        if not ta_text:
            logger.warning(f"技术分析不可用，继续量化回测：{last_err}")

        # 首日提示：仅输出关键节点
        if not first_day_debug_done:
            o = df.iloc[i]['open'] if 'open' in df.columns else None
            h = df.iloc[i]['high'] if 'high' in df.columns else None
            l = df.iloc[i]['low'] if 'low' in df.columns else None
            def _fmt(v):
                return "N/A" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{float(v):.2f}"
            print(f"启动回测 | 首日 {date_str} OHLC: O={_fmt(o)} H={_fmt(h)} L={_fmt(l)} C={_fmt(price)}")
            print("节点：向 DeepSeek 发起决策请求；若配置 Dify，将并行获取技术分析。")

        # LLM 调用：连续失败3次后暂停并交互确认是否继续
        if 'llm_fail_consecutive' not in locals():
            llm_fail_consecutive = 0
        while True:
            try:
                t0 = time.time()
                decisions = ai_trade_decision_provider(md_dict, pf_json, model_name=model_name)
                t1 = time.time()
                llm_ms = int((t1 - t0) * 1000)

                decision_obj = decisions.get(symbol, {})
                args = decision_obj.get('trade_signal_args', {}) or {}
                llm_raw_text = str(decision_obj.get('_raw_text', '') or '')
                llm_raw_records.append({"date": date_str, "symbol": symbol, "content": llm_raw_text})

                # 兼容 signal/action，两者选其一，统一为小写
                raw_signal = args.get('signal') or args.get('action') or 'hold'
                signal = str(raw_signal).lower().strip()
                # 同义词规范化
                if signal in ('long', 'buy_open', 'open_long'):
                    signal = 'buy'
                elif signal in ('short', 'sell_open', 'open_short'):
                    signal = 'sell'
                elif signal in ('wait', 'stay', 'idle', 'nop'):
                    signal = 'hold'

                # 数量与杠杆兜底（数量按“手”，随后转为股）
                quantity_lots = int(float(args.get('quantity', 0.0) or 0.0))
                leverage = float(args.get('leverage', 1.0) or 1.0)
                entry_price = price
                reasoning = str(decision_obj.get('reasoning', '') or '')

                # 本地执行前的硬约束：冷却期禁止买入；下跌阶段总持仓≤3手
                try:
                    flags = compute_strategy_flags(md_one)
                except Exception:
                    flags = {}
                if signal == 'buy' and md_one.get('buy_cooldown', False):
                    signal = 'hold'
                    quantity_lots = 0
                if signal == 'buy' and bool(flags.get('is_in_downtrend_cap')):
                    cap_remaining = max(0, 3 - current_position_lots)
                    if quantity_lots > cap_remaining:
                        quantity_lots = cap_remaining
                    if quantity_lots <= 0:
                        signal = 'hold'
                        quantity_lots = 0

                # 超买优先级：禁止任何买入；若有仓且可卖，则优先减仓
                allowed_date = can_sell_after.get(symbol)
                tplus1_sell_available_today = bool(allowed_date and dstr >= allowed_date)
                if bool(flags.get('is_overbought_sell')):
                    if signal == 'buy':
                        if current_position_lots > 0 and tplus1_sell_available_today:
                            signal = 'sell'
                            quantity_lots = max(1, int(math.floor(current_position_lots * 0.5)))
                        else:
                            signal = 'hold'
                            quantity_lots = 0

                # 5日内加仓次数上限≤2：超过则拒绝买入
                try:
                    idx_cur = open_days.index(dstr)
                    win_days = set(open_days[max(0, idx_cur - 5): idx_cur])
                    buys_in_window = sum(1 for a in actions if a.get('date') and a.get('date').replace('-', '') in win_days and str(a.get('signal')).lower() == 'buy')
                except Exception:
                    buys_in_window = 0
                if signal == 'buy' and buys_in_window >= 2:
                    signal = 'hold'
                    quantity_lots = 0

                # EMA20 邻近加仓：有仓时加仓需接近 EMA20，扩张态拒绝
                try:
                    ema20_close = md_one.get('current_close_20_ema')
                    if signal == 'buy' and current_position_lots > 0 and ema20_close is not None and float(ema20_close) > 0:
                        ratio = float(price) / float(ema20_close)
                        if ratio >= 1.03:
                            signal = 'hold'
                            quantity_lots = 0
                except Exception:
                    pass

                # 涨跌停禁买：当日相对昨收涨跌幅绝对值≥9.8%时拒绝买入
                try:
                    prev_close = float(df.iloc[i - 1]['close']) if i - 1 >= 0 else None
                    if prev_close and prev_close > 0:
                        chg_pct = (price - prev_close) / prev_close
                        if signal == 'buy' and abs(chg_pct) >= 0.098:
                            signal = 'hold'
                            quantity_lots = 0
                except Exception:
                    pass

                # 生成并保存当日 LLM 决策 JSON（按日期唯一覆盖）
                try:
                    market_prompt_str = build_market_prompt(symbol, md_one, pf_json)
                except Exception:
                    market_prompt_str = None
                llm_obj = _load_json(llm_json_path)
                # 顶层以日期为键，便于覆盖
                rec = {
                    "date": date_str,
                    "symbol": symbol,
                    "model_name": model_name,
                    "market_prompt": market_prompt_str,
                    "reasoning": reasoning,
                    "raw_text": llm_raw_text,
                    "decision": decision_obj
                }
                try:
                    llm_obj[date_str] = rec
                    _save_json(llm_json_path, llm_obj)
                except Exception as e:
                    print(f"⚠️ 保存 LLM 决策 JSON 失败：{e}")

                # 追加 NDJSON 审计（每日一行，完整包含 prompts/reasoning/raw/decision）
                if llm_ndjson:
                    try:
                        nd_line = {
                            "date": date_str,
                            "symbol": symbol,
                            "model_name": model_name,
                            "llm_ms": llm_ms,
                            "system_prompt": SYSTEM_PROMPT_TEXT,
                            "market_prompt": market_prompt_str,
                            "reasoning": reasoning,
                            "raw_text": llm_raw_text,
                            "decision": decision_obj,
                            "llm_state": md_one.get('llm_state', {})
                        }
                        with open(llm_ndjson_path, 'a', encoding='utf-8') as fnd:
                            fnd.write(json.dumps(nd_line, ensure_ascii=False) + "\n")
                        # 终端不打印 NDJSON，避免噪音；审计仅写盘
                        # 上传 NDJSON 到 R2（若配置），严格模式下失败即停
                        pass
                    except Exception as e:
                        print(f"⚠️ 追加 NDJSON 审计失败：{e}")

                # 返回摘要提示
                # 关键节点：LLM 返回决策
                print(f"节点：LLM 返回 | {date_str} signal={signal} qty(lots)={quantity_lots} lev={leverage:.2f} 耗时={llm_ms}ms")
                first_day_debug_done = True

                # 成功后重置连续失败计数并退出重试循环
                llm_fail_consecutive = 0
                break

            except Exception as e:
                llm_fail_consecutive = (llm_fail_consecutive or 0) + 1
                logger.error(f"DeepSeek 决策失败（第{llm_fail_consecutive}次）：{e}")
                if llm_fail_consecutive >= 3:
                    print("LLM 连续失败3次。按回车继续重试，或输入 q 退出当前标的回测。")
                    try:
                        user_inp = input("继续重试请直接回车；退出请输入 q: ").strip().lower()
                    except Exception:
                        user_inp = ''
                    if user_inp == 'q':
                        print("用户选择退出该标的回测。")
                        return {}
                    else:
                        # 用户确认继续：重置失败计数，立即重试
                        llm_fail_consecutive = 0
                        continue
                else:
                    # 前两次失败：指数退避等待后重试
                    backoff_sec = min(60, 2 ** llm_fail_consecutive)
                    print(f"LLM 决策调用失败，将在 {backoff_sec}s 后重试（第{llm_fail_consecutive}次）。")
                    try:
                        time.sleep(backoff_sec)
                    except Exception:
                        pass
                    continue

        # A股规则：仅做多；卖出为减仓或平仓，需满足T+1
        current_qty = 0.0
        if hasattr(portfolio, 'positions') and symbol in portfolio.positions:
            try:
                current_qty = float(getattr(portfolio.positions[symbol], 'quantity', 0.0))
            except Exception:
                current_qty = 0.0

        # 处理卖出：支持部分减仓（sell）与全平（close）
        if signal in ('sell', 'close'):
            if current_qty <= 0.0:
                print(f"⚠️  {symbol}: A股不支持空头卖出，当前无持仓，忽略卖出/平仓信号。")
                signal = 'hold'
                quantity = 0.0
            else:
                allowed_date = can_sell_after.get(symbol)
                if allowed_date and dstr < allowed_date:
                    print(f"⚠️  {symbol}: T+1 未到，可卖出日 {allowed_date}，今日忽略卖出/平仓。")
                    signal = 'hold'
                    quantity = 0.0
                else:
                    if signal == 'close':
                        # 全平仓：数量为当前持仓
                        quantity = int(current_qty)
                    else:
                        # 部分减仓：按手数转换与限幅
                        max_sellable_lots = int(current_qty // lot_size)
                        if quantity_lots > max_sellable_lots:
                            quantity_lots = max_sellable_lots
                        if quantity_lots < 1:
                            signal = 'hold'
                            quantity = 0
                        else:
                            quantity = quantity_lots * lot_size

        # 买入遵循现金约束 + A股按手处理：LLM 返回的是手数（包含滑点影响）
        if signal == 'buy':
            # 预扣费用后的最大可买手数（佣金 + 过户费），避免买入后现金因费用为负
            fees_rate = (commission_rate + (transfer_fee_rate if is_shanghai else 0.0))
            try:
                slippage_buy_pct = float(os.getenv('SLIPPAGE_BUY_PCT', '0.01'))
            except Exception:
                slippage_buy_pct = 0.01
            per_lot_total = entry_price * (1.0 + slippage_buy_pct) * lot_size * (1.0 + fees_rate)
            max_buyable_lots = int(portfolio.available_cash // per_lot_total)
            if quantity_lots > max_buyable_lots:
                quantity_lots = max_buyable_lots
            if quantity_lots < 1:
                signal = 'hold'
                quantity = 0
            else:
                quantity = quantity_lots * lot_size
                # 买入成交价采用含滑点的有效价格
                entry_price = entry_price * (1.0 + slippage_buy_pct)
                # 现实化成交价：夹逼在当日最高/最低之间
                try:
                    if day_high is not None and day_low is not None:
                        entry_price = max(day_low, min(day_high, entry_price))
                    elif day_high is not None:
                        entry_price = min(day_high, entry_price)
                    elif day_low is not None:
                        entry_price = max(day_low, entry_price)
                except Exception:
                    pass
        elif signal == 'hold':
            # 保持不动：数量明确为0，避免未初始化
            quantity = 0
        elif signal in ('sell', 'close'):
            # 卖出/平仓采用负滑点的有效价格
            try:
                slippage_sell_pct = float(os.getenv('SLIPPAGE_SELL_PCT', '0.01'))
            except Exception:
                slippage_sell_pct = 0.01
            entry_price = entry_price * (1.0 - slippage_sell_pct)
            # 现实化成交价：夹逼在当日最高/最低之间
            try:
                if day_high is not None and day_low is not None:
                    entry_price = max(day_low, min(day_high, entry_price))
                elif day_high is not None:
                    entry_price = min(day_high, entry_price)
                elif day_low is not None:
                    entry_price = max(day_low, entry_price)
            except Exception:
                pass

        # 执行到组合（在卖出/平仓前先保存入场均价以便统计）
        prev_entry_price = None
        if signal in ('sell', 'close') and symbol in portfolio.positions:
            try:
                prev_entry_price = float(getattr(portfolio.positions[symbol], 'entry_price', None) or 0.0)
            except Exception:
                prev_entry_price = None
        # 执行前采集现金与持仓快照（用于 trades 入库）
        try:
            cash_before = float(getattr(portfolio, 'available_cash', 0.0))
        except Exception:
            cash_before = None
        try:
            position_before = float(current_qty)
        except Exception:
            position_before = None

        ok = portfolio.execute_decision(
            symbol=symbol,
            quantity=quantity,
            price=entry_price,
            leverage=leverage,
            signal=signal
        )

        action_pnl = None
        # 交易费用处理（按金额）
        try:
            if ok and signal == 'buy' and quantity > 0:
                trade_amount = quantity * entry_price  # entry_price 已包含滑点
                commission_amt = trade_amount * commission_rate
                transfer_amt = trade_amount * (transfer_fee_rate if is_shanghai else 0.0)
                fees = commission_amt + transfer_amt
                portfolio.available_cash -= fees
                portfolio._update_total_asset()
                # 累计费用
                total_commission += commission_amt
                total_transfer += transfer_amt
                # 终端提示：买入明细
                print(f"执行：买入 {symbol} {quantity}股（{quantity // lot_size}手），成交金额 {trade_amount:.2f}（含滑点），佣金 {commission_amt:.2f}，过户费 {transfer_amt:.2f}，总成本 {trade_amount + fees:.2f}。当前持仓 {int(getattr(portfolio.positions.get(symbol, None), 'quantity', 0))}股。")
                action_pnl = 0.0
            elif ok and signal == 'close':
                # 已平仓：使用历史持仓数量计算卖出金额
                closed_qty = current_qty
                trade_amount = closed_qty * entry_price
                commission_amt = trade_amount * commission_rate
                transfer_amt = trade_amount * (transfer_fee_rate if is_shanghai else 0.0)
                stamp_duty_amt = trade_amount * stamp_duty_rate
                fees = commission_amt + transfer_amt + stamp_duty_amt
                portfolio.available_cash -= fees
                portfolio._update_total_asset()
                net_received = trade_amount - fees
                # 累计费用
                total_commission += commission_amt
                total_transfer += transfer_amt
                total_stamp += stamp_duty_amt
                # 交易统计（毛盈亏不含费用）
                trades_total += 1
                if prev_entry_price is not None:
                    diff = closed_qty * (entry_price - prev_entry_price)
                    if diff > 0:
                        trades_won += 1
                        gross_profit_total += diff
                    elif diff < 0:
                        trades_lost += 1
                        gross_loss_total += abs(diff)
                    action_pnl = diff - fees
                else:
                    action_pnl = None
                # 终端提示：卖出明细
                print(f"执行：卖出平仓 {symbol} {int(closed_qty)}股（{int(closed_qty) // lot_size}手），成交金额 {trade_amount:.2f}（含滑点），佣金 {commission_amt:.2f}，过户费 {transfer_amt:.2f}，印花税 {stamp_duty_amt:.2f}，净回收 {net_received:.2f}。当前持仓 0 股。")
            elif ok and signal == 'sell' and quantity > 0:
                # 部分减仓费用与统计
                sold_qty = int(quantity)
                trade_amount = sold_qty * entry_price
                commission_amt = trade_amount * commission_rate
                transfer_amt = trade_amount * (transfer_fee_rate if is_shanghai else 0.0)
                stamp_duty_amt = trade_amount * stamp_duty_rate
                fees = commission_amt + transfer_amt + stamp_duty_amt
                portfolio.available_cash -= fees
                portfolio._update_total_asset()
                net_received = trade_amount - fees
                # 累计费用
                total_commission += commission_amt
                total_transfer += transfer_amt
                total_stamp += stamp_duty_amt
                # 交易统计（毛盈亏不含费用）
                trades_total += 1
                if prev_entry_price is not None:
                    diff = sold_qty * (entry_price - prev_entry_price)
                    if diff > 0:
                        trades_won += 1
                        gross_profit_total += diff
                    elif diff < 0:
                        trades_lost += 1
                        gross_loss_total += abs(diff)
                    action_pnl = diff - fees
                else:
                    action_pnl = None
                # 终端提示：部分减仓明细
                remaining_qty = int(getattr(portfolio.positions.get(symbol, None), 'quantity', 0))
                print(f"执行：部分减仓 {symbol} {sold_qty}股（{sold_qty // lot_size}手），成交金额 {trade_amount:.2f}（含滑点），佣金 {commission_amt:.2f}，过户费 {transfer_amt:.2f}，印花税 {stamp_duty_amt:.2f}，净回收 {net_received:.2f}。当前持仓 {remaining_qty} 股。")
        except Exception:
            pass

        # 若今日成功开多仓，记录可卖出日期为“下一交易日”（T+1）
        if ok and signal == 'buy':
            try:
                idx_in_days = open_days.index(dstr)
                next_open = open_days[idx_in_days + 1] if idx_in_days + 1 < len(open_days) else None
                if next_open:
                    can_sell_after[symbol] = next_open
            except ValueError:
                pass

        # 冷却状态机更新：探索买入或卖出/平仓后，设置 buy_cooldown_until 为未来3个开放日
        try:
            idx_in_days = open_days.index(dstr)
        except Exception:
            idx_in_days = None
        if ok and idx_in_days is not None:
            # 卖出/平仓后进入冷却
            if signal in ('sell', 'close'):
                try:
                    next_idx = min(idx_in_days + 3, len(open_days) - 1)
                    buy_cooldown_until = open_days[next_idx]
                except Exception:
                    pass
            # 探索买入（非严格趋势）后进入冷却
            elif signal == 'buy':
                try:
                    flags = compute_strategy_flags(md_one)
                except Exception:
                    flags = {}
                is_trend_buy_strict = bool(flags.get('is_trend_buy_strict'))
                is_exploratory_buy = bool(flags.get('is_exploratory_buy'))
                if (not is_trend_buy_strict) and is_exploratory_buy:
                    try:
                        next_idx = min(idx_in_days + 3, len(open_days) - 1)
                        buy_cooldown_until = open_days[next_idx]
                    except Exception:
                        pass

        # 趋势失效联动：若趋势失效且可卖，强制部分减仓≥50%
        try:
            flags = compute_strategy_flags(md_one)
        except Exception:
            flags = {}
        allowed_date = can_sell_after.get(symbol)
        tplus1_sell_available_today = bool(allowed_date and dstr >= allowed_date)
        if signal != 'hold' and bool(flags.get('is_trend_invalidation_sell')) and current_position_lots > 0 and tplus1_sell_available_today:
            signal = 'sell'
            quantity_lots = max(1, int(math.floor(current_position_lots * 0.5)))

        # 执行后采集现金与持仓（用于 trades/daily_metrics 入库）
        try:
            position_after = float(getattr(portfolio.positions.get(symbol, None), 'quantity', 0.0))
        except Exception:
            position_after = None
        try:
            cash_after = float(getattr(portfolio, 'available_cash', None))
        except Exception:
            cash_after = None

        eff_price = entry_price if ok and signal in ('buy','sell','close') else price
        actions.append({
            'date': date_str,
            'price': price,
            'signal': signal,
            'quantity': quantity,
            'leverage': leverage,
            'success': ok,
            'available_cash': portfolio.available_cash,
            'total_asset': portfolio.total_asset,
            'llm_ms': llm_ms,
            'reasoning_excerpt': '' if hide_reasoning else reasoning[:500], 'effective_price': eff_price, 'pnl': action_pnl
        })

        # 逐日追加交易结果到 CSV
        # 交易 CSV：按日期唯一覆盖
        eff_price = entry_price if ok and signal in ('buy','sell','close') else price
        _upsert_trades_csv(
            trades_csv_path,
            header="date,price,signal,quantity,leverage,success,available_cash,total_asset,llm_ms,effective_price",
            date_key=date_str,
            line=f"{date_str},{price:.4f},{signal},{int(quantity)},{leverage:.2f},{1 if ok else 0},{portfolio.available_cash:.2f},{portfolio.total_asset:.2f},{llm_ms},{eff_price:.4f}"
        )

        ok_u_j, err_u_j = _r2_upload(llm_json_path, key_prefix='aitrading', run_id=run_id, symbol=symbol, start_date=start_date, end_date=dstr)
        if not ok_u_j:
            print(f"⚠️ R2 上传失败：{err_u_j}")
            _supabase_insert_error(run_id, symbol, dstr, source='r2', code='r2_upload_failed', message=str(err_u_j))
            if strict_deps:
                print("严格模式：外部依赖失败即停。")
                return {}
        else:
            print(f"[WEB] R2 上传成功 | key=aitrading/{symbol}/{dstr}/{os.path.basename(llm_json_path)}")

        ok_u_c, err_u_c = _r2_upload(trades_csv_path, key_prefix='aitrading', run_id=run_id, symbol=symbol, start_date=start_date, end_date=dstr)
        if not ok_u_c:
            print(f"⚠️ R2 上传失败：{err_u_c}")
            _supabase_insert_error(run_id, symbol, dstr, source='r2', code='r2_upload_failed', message=str(err_u_c))
            if strict_deps:
                print("严格模式：外部依赖失败即停。")
                return {}
        else:
            print(f"[WEB] R2 上传成功 | key=aitrading/{symbol}/{dstr}/{os.path.basename(trades_csv_path)}")

        # 自动写入 Supabase：trades + daily_metrics（失败可选择即停）
        row_doc = {
            'date': date_str,
            'price': price,
            'signal': signal,
            'quantity': quantity,
            'effective_price': eff_price,
            'cash_before': cash_before,
            'cash_after': cash_after,
            'position_before': position_before,
            'position_after': position_after,
            'pnl': None,
            'note': f"llm_ms={llm_ms};success={(1 if ok else 0)}",
        }
        t_ok, t_err = _supabase_upsert_trade(run_id, symbol, date_str, row_doc)
        d_ok, d_err = _supabase_upsert_daily_metrics(
            run_id, symbol, date_str,
            cash=cash_after,
            equity=float(portfolio.total_asset),
            position=position_after,
            initial_cash=float(getattr(portfolio, 'initial_cash', 0.0))
        )
        o_ok, o_err = _supabase_upsert_ohlc(run_id, symbol, date_str, day_open, day_high, day_low, price)
        if not t_ok or not d_ok:
            msg = t_err or d_err
            print(f"⚠️ 云端入库失败：{msg}")
            _supabase_insert_error(run_id, symbol, dstr, source='supabase', code='supabase_upsert_failed', message=str(msg))
            if strict_deps:
                print("严格模式：外部依赖失败即停。")
                return {}
        if not o_ok:
            msg = o_err
            print(f"⚠️ 云端入库失败：{msg}")
            _supabase_insert_error(run_id, symbol, dstr, source='supabase', code='supabase_upsert_failed', message=str(msg))
            if strict_deps:
                print("严格模式：外部依赖失败即停。")
                return {}
        else:
            if t_ok:
                print(f"[WEB] Supabase trades 入库成功 | symbol={symbol} date={date_str}")
            if d_ok:
                print(f"[WEB] Supabase daily_metrics 入库成功 | symbol={symbol} date={date_str}")
            if o_ok:
                print(f"[WEB] Supabase ohlc 入库成功 | symbol={symbol} date={date_str}")

        print(f"{date_str}  {price:8.2f}  {signal:<6}  {quantity:10.4f}  {portfolio.available_cash:12.2f}  {portfolio.total_asset:12.2f}  {llm_ms:8d}")

        # 进入下一交易日前的节拍提示与等待
        # 更明确：提示下一交易日日期
        try:
            idx_in_days = open_days.index(dstr)
            next_open = open_days[idx_in_days + 1] if idx_in_days + 1 < len(open_days) else None
            next_date_str = pd.to_datetime(next_open, format='%Y%m%d').strftime('%Y-%m-%d') if next_open else '无'
        except Exception:
            next_date_str = '无'
        try:
            ss = int(sleep_seconds)
        except Exception:
            ss = 0
        if ss > 0:
            print(f"节点：等待 {ss}s 后进入下一交易日（{next_date_str}）")
            try:
                time.sleep(ss)
            except Exception:
                pass
        else:
            print(f"节点：继续下一交易日 → {next_date_str}")

        # 更新进度：最后处理到当日
        try:
            progress_obj['symbol'] = symbol
            progress_obj['start_date'] = start_date
            progress_obj['last_processed_date'] = dstr
            progress_obj['last_available_date'] = df['date_str'].iloc[-1] if not df.empty else None
            progress_obj['model_name'] = model_name
            progress_obj['data_source'] = 'tinyshare'
            progress_obj['updated_at'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            progress_obj['can_sell_after'] = can_sell_after
            progress_obj['buy_cooldown_until'] = buy_cooldown_until
            _save_json(progress_json_path, progress_obj)
            try:
                portfolio.save_to_file(portfolio_state_path)
            except Exception:
                pass
            # 云端 checkpoint：记录进行中状态
            c_ok, c_err = _supabase_upsert_checkpoint(run_id, symbol, dstr, reason='in_progress')
            if not c_ok:
                print(f"⚠️ 写入 checkpoint 失败：{c_err}")
                _supabase_insert_error(run_id, symbol, dstr, source='supabase', code='checkpoint_upsert_failed', message=str(c_err))
                if strict_deps:
                    print("严格模式：外部依赖失败即停。")
                    return {}
        except Exception:
            print("⚠️ 更新进度文件失败")

    # 汇总结果
    # 汇总统计
    total_fees = total_commission + total_transfer + total_stamp
    net_pnl = float(portfolio.total_asset - portfolio.initial_cash)
    profit_factor = None
    if gross_loss_total > 1e-8:
        profit_factor = gross_profit_total / gross_loss_total
    elif trades_total > 0 and gross_loss_total <= 1e-8:
        profit_factor = float('inf')

    # 运行结束：写入停机原因
    try:
        today_str = pd.Timestamp.now().strftime('%Y%m%d')
        last_data_day = df['date_str'].iloc[-1] if not df.empty else None
        # 今天是否交易日
        is_today_open = today_str in open_days
        # 是否今天存在数据
        has_today_data = (today_str in idx_map)
        stop_reason = None
        if is_today_open and not has_today_data:
            stop_reason = 'no_data_for_today'
        elif not is_today_open:
            stop_reason = 'non_trading_day'
        else:
            stop_reason = 'completed'
        progress_obj['stop_reason'] = stop_reason
        progress_obj['today'] = today_str
        progress_obj['last_available_date'] = last_data_day
        progress_obj['updated_at'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        _save_json(progress_json_path, progress_obj)
        # 更新 runs 状态
        status_to_update = 'completed' if stop_reason in ('completed', 'non_trading_day', 'no_data_for_today') else stop_reason
        r_ok, r_err = _supabase_update_run_status(run_id, status=status_to_update)
        if not r_ok:
            print(f"⚠️ 更新 runs 状态失败：{r_err}")
            _supabase_insert_error(run_id, symbol, today_str, source='supabase', code='runs_update_failed', message=str(r_err))
            if strict_deps:
                print("严格模式：外部依赖失败即停。")
                return {}
    except Exception:
        pass

    result = {
        'symbol': symbol,
        'start': start_date,
        'end': end_date,
        'initial_cash': portfolio.initial_cash,
        'final_total_asset': portfolio.total_asset,
        'total_pnl': portfolio.total_pnl(),
        'actions': actions,
        # 费用与统计
        'fees': {
            'commission': round(total_commission, 2),
            'transfer': round(total_transfer, 2),
            'stamp_duty': round(total_stamp, 2),
            'total': round(total_fees, 2)
        },
        'stats': {
            'trades_total': trades_total,
            'trades_won': trades_won,
            'trades_lost': trades_lost,
            'gross_profit': round(gross_profit_total, 2),
            'gross_loss': round(gross_loss_total, 2),
            'profit_factor': None if profit_factor is None else round(profit_factor, 3),
            'net_pnl': round(net_pnl, 2),
            'win_rate': None if trades_total == 0 else round(trades_won / trades_total, 3)
        }
    }
    # 标记 LLM 原始输出审计文件（已在每次请求后即时写入）
    try:
        result['llm_json'] = llm_json_path
        result['trades_csv'] = trades_csv_path
        result['progress_json'] = progress_json_path
        result['llm_ndjson'] = llm_ndjson_path if llm_ndjson else None
        print(f"LLM 决策与交易记录写入：{llm_json_path} 与 {trades_csv_path}；进度：{progress_json_path}")
        if llm_ndjson:
            print(f"NDJSON 审计：{llm_ndjson_path}")
        # 收尾：上传关键输出到 R2
        for pth in [llm_json_path, trades_csv_path]:
            if pth:
                ok_u, err_u = _r2_upload(pth, key_prefix='aitrading', run_id=run_id, symbol=symbol, start_date=start_date, end_date=end_date)
                if not ok_u:
                    print(f"⚠️ 收尾上传 R2 失败：{err_u}")
                    _supabase_insert_error(run_id, symbol, end_date, source='r2', code='r2_upload_failed', message=str(err_u))
                    if strict_deps:
                        print("严格模式：外部依赖失败即停。")
                        return {}
    except Exception as e:
        print(f"⚠️ 标记输出文件路径失败：{e}")
    return result

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=False, help='股票代码（不含交易所后缀）例如 600519')
    parser.add_argument('--stocklist', required=False, help='CSV 文件路径，包含表头：stock_code,start_date，[end_date 可选，缺省为今天]')
    parser.add_argument('--start', help='开始日期 YYYYMMDD')
    parser.add_argument('--end', help='结束日期 YYYYMMDD（缺省为今天）')
    # 新增：控制输出与等待
    parser.add_argument('--hide-prompts', action='store_true', help='隐藏系统/市场提示词输出')
    parser.add_argument('--hide-reasoning', action='store_true', help='隐藏 DeepSeek 的 reasoning 文本')
    parser.add_argument('--quiet', action='store_true', help='安静模式：同时隐藏提示词与 reasoning，仅输出摘要')
    parser.add_argument('--llm-ndjson', action='store_true', help='将 LLM 决策审计以 NDJSON 持久化并逐日单行打印')
    parser.add_argument('--sleep-seconds', type=int, default=3, help='每个交易日间的等待秒数')
    parser.add_argument('--strict-deps', action='store_true', help='严格依赖：云端失败即停')
    # 新增：初始资金与费用参数、最小交易单位
    parser.add_argument('--cash', type=float, default=100000.0, help='初始资金，默认10万元')
    parser.add_argument('--lot-size', type=int, default=100, help='A股最小交易单位（股），默认100股')
    parser.add_argument('--commission-rate', type=float, default=0.0003, help='佣金费率，默认万3=0.03%')
    parser.add_argument('--stamp-duty-rate', type=float, default=0.0005, help='印花税（仅卖出），默认0.05%')
    parser.add_argument('--transfer-fee-rate', type=float, default=0.00001, help='过户费（双边），默认0.01‰=0.00001')
    # 新增：交互模式与模型选择
    parser.add_argument('--interactive', action='store_true', help='启用交互式输入（选择模型与起止日期）')
    parser.add_argument('--model', choices=['deepseek-chat', 'deepseek-reasoner'], help='指定 DeepSeek 模型；若启用交互可忽略')

    args = parser.parse_args()
    symbol = args.symbol
    stocklist = args.stocklist
    start_date = args.start
    end_date = args.end
    hide_prompts = args.hide_prompts
    hide_reasoning = args.hide_reasoning
    # quiet 合并隐藏项
    if getattr(args, 'quiet', False):
        hide_prompts = True
        hide_reasoning = True
    llm_ndjson_flag = getattr(args, 'llm_ndjson', False)
    sleep_seconds = args.sleep_seconds
    strict_deps = getattr(args, 'strict_deps', False) or bool(os.getenv('STRICT_DEPS'))
    cash = args.cash
    lot_size = args.lot_size
    commission_rate = args.commission_rate
    stamp_duty_rate = args.stamp_duty_rate
    transfer_fee_rate = args.transfer_fee_rate
    interactive = args.interactive
    model_name = args.model or os.getenv('LLM_MODEL') or 'deepseek-chat'

    # 交互式输入：允许在终端输入模型与日期，避免频繁敲命令
    def _read_date(prompt: str, default_val: str = None) -> str:
        while True:
            s = input(prompt).strip() if default_val is None else input(f"{prompt} (默认 {default_val}): ").strip() or default_val
            s = s.replace('-', '')
            if len(s) == 8 and s.isdigit():
                return s
            print("输入格式应为 YYYYMMDD，例如 20250101。请重试。")

    if interactive and not stocklist:
        print("请选择模型：1=deepseek-chat，2=deepseek-reasoner")
        sel = input("请输入 1 或 2: ").strip()
        if sel == '2':
            model_name = 'deepseek-reasoner'
            # 选择 reasoner 时，默认隐藏系统/市场提示词与 reasoning 文本，保持终端简洁
            hide_prompts = True
            hide_reasoning = True
        else:
            model_name = 'deepseek-chat'
        # 起止日期交互输入
        start_date = _read_date("请输入开始日期 YYYYMMDD")
        end_date = _read_date("请输入结束日期 YYYYMMDD")
    else:
        # 非交互：至少提供开始日期；结束日期缺省为今天
        if (not stocklist) and (not start_date):
            print("缺少 --start 且未启用 --interactive。请提供开始日期或使用交互模式。")
            sys.exit(2)
        if not end_date:
            try:
                end_date = pd.Timestamp.now().strftime('%Y%m%d')
                print(f"结束日期缺省为今天：{end_date}")
            except Exception:
                print("无法获取当前日期用作结束日期")
                sys.exit(2)

    # 先配置日志，再执行一次回测（删除重复调用）
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    def _print_summary(result: Dict[str, Any]):
        if not result:
            print("节点：回测失败或数据为空")
            return
        # 结束节点：简要信息与文件路径，不打印详细摘要与汇总表
        print("\n节点：回测结束")
        print(f"symbol={result.get('symbol')} start={result.get('start')} end={result.get('end')}")
        print(f"final_total_asset={result.get('final_total_asset'):.2f} total_pnl={result.get('total_pnl'):.2f}")
        paths = [result.get('llm_json'), result.get('trades_csv'), result.get('progress_json'), result.get('llm_ndjson')]
        print("输出文件：")
        for p in paths:
            if p:
                print(f" - {p}")

    # 执行：支持 CSV 批量或单标
    if stocklist:
        try:
            # 读取后统一规范列名与类型；支持缺少 end_date
            df_list = pd.read_csv(stocklist)
        except Exception as e:
            print(f"无法读取 stocklist CSV：{e}")
            sys.exit(2)
        # 规范化列名
        df_list.columns = [c.strip().lower() for c in df_list.columns]
        required_cols = {'stock_code', 'start_date'}
        if not required_cols.issubset(set(df_list.columns)):
            print(f"CSV 缺少必要表头：{required_cols}；可选：end_date（缺省为今天）")
            sys.exit(2)
        # 强制类型为字符串，保留前导零
        if 'stock_code' in df_list.columns:
            df_list['stock_code'] = df_list['stock_code'].astype(str)
        if 'start_date' in df_list.columns:
            df_list['start_date'] = df_list['start_date'].astype(str)
        if 'end_date' in df_list.columns:
            df_list['end_date'] = df_list['end_date'].astype(str)
        # 默认结束日期为今天（YYYYMMDD）
        today_str = pd.Timestamp.today().strftime('%Y%m%d')
        for i, row in df_list.iterrows():
            sym = str(row['stock_code']).strip()
            st = str(row['start_date']).strip()
            ed = str((row['end_date'] if 'end_date' in df_list.columns else '') or '').strip()
            if not sym or not st:
                print(f"跳过第{i}行：存在空值 sym={sym}, start={st}")
                continue
            if not ed:
                ed = today_str
                print(f"第{i}行未提供 end_date，默认使用今天：{ed}")
            # 规范化代码（补齐6位并确定交易所），内部 run_backtest 会再次统一
            base_sym, _exch = normalize_symbol(sym)
            sym = base_sym
            print(f"\n==== 批量回测：{sym} {st}~{ed} ====")
            result = run_backtest(sym, st, ed,
                                  hide_prompts=hide_prompts,
                                  hide_reasoning=hide_reasoning,
                                  sleep_seconds=sleep_seconds,
                                  initial_cash=cash,
                                  lot_size=lot_size,
                                  commission_rate=commission_rate,
                                  stamp_duty_rate=stamp_duty_rate,
                                  transfer_fee_rate=transfer_fee_rate,
                                  model_name=model_name,
                                  llm_ndjson=llm_ndjson_flag,
                                  strict_deps=strict_deps)
            _print_summary(result)
        return
    else:
        result = run_backtest(symbol, start_date, end_date,
                              hide_prompts=hide_prompts,
                              hide_reasoning=hide_reasoning,
                              sleep_seconds=sleep_seconds,
                              initial_cash=cash,
                              lot_size=lot_size,
                              commission_rate=commission_rate,
                              stamp_duty_rate=stamp_duty_rate,
                              transfer_fee_rate=transfer_fee_rate,
                              model_name=model_name,
                              llm_ndjson=llm_ndjson_flag,
                              strict_deps=strict_deps)
        if not result:
            print("回测失败或数据为空")
            sys.exit(1)
        _print_summary(result)


if __name__ == '__main__':
    main()