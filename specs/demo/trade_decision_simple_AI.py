"Trading Decision Provider - Generates trading signals based on market data"
from typing import Dict, Any
import json
import math
import os
import time
import requests
import dotenv
dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_MODEL_ENV = os.getenv("LLM_MODEL")

# 模块级：新增 build_market_prompt（导出给 backtest.py 使用）
JSON_FORMAT_INSTRUCTIONS = (
    "\n*** 实盘交易执行定价（关键） ***\n"
    "你正在下达真实的交易订单。为了确保在市场波动中成交：\n"
    "- **买入订单 (BUY)**：设置 'limit_price' 比当前价高 1%~2%。（例如：当前价100，limit_price=101.5）。如果急于入场（超级趋势），可设高 2%。\n"
    "- **卖出订单 (SELL)**：设置 'limit_price' 比当前价低 1%~2%。（例如：当前价100，limit_price=98.5）。如果趋势破位，设低 2% 以确保逃顶。\n"
    "- **持有 (HOLD)**：limit_price = 0。\n"
    "\n"
    "请严格输出 JSON 格式，包含 'trade_signal_args' 键：\n"
    "{\n"
    "  'symbol': '...', 'signal': '...', 'quantity': 整数手数 (Integer Lots, NOT Shares! 1手=100股. e.g. output 15 for 1500 shares),\n"
    "  'confidence': float,\n"
    "  'limit_price': float,\n"
    "  'stop_loss': float, 'invalidation_condition': '...'\n"
    "}"
)

SYSTEM_PROMPT_TEXT = (
    "你是一个A股量化交易智能体。你必须严格基于数学指标和市场结构做出决策。\n"
    "你的目标是捕捉趋势并避免大幅回撤。\n"
    "\n"
    "*** 决策框架 ***\n"
    "分析提供的市场数据（OHLC, EMA, MACD, RSI等）和持仓状态。\n"
    "\n"
    "1. 趋势识别：\n"
    "   - **上升趋势**：价格 > EMA20, MACD > 0, 高点/低点抬高。\n"
    "   - **下降趋势**：价格 < EMA20, MACD < 0, 高点/低点降低。\n"
    "\n"
    "2. 入场信号 (BUY)：\n"
    "   - **趋势跟随**：价格带量突破 EMA20。MACD 柱状图翻红且上升。RSI > 50 但 < 70。\n"
    "   - **回调买入**：上升趋势中，价格回踩 EMA20 或布林带中/下轨并反弹。RSI 回落至 40-50。\n"
    "   - **动能突破**：强势突破，RSI 上升（但 < 80）。\n"
    "\n"
    "3. 离场信号 (SELL/CLOSE)：\n"
    "   - **趋势反转**：价格连续2日收盘低于 EMA20。这是硬性离场规则。\n"
    "   - **动能衰竭**：MACD 柱状图背离（价高但动能弱）。RSI 从超买区回落。\n"
    "   - **超买**：RSI > 80 提示风险，考虑部分止盈。\n"
    "   - **止损**：价格跌破预设止损位（如 -5%）。\n"
    "\n"
    "*** 执行规则 ***\n"
    "- **买入**：\n"
    "   - 仅在有可用现金时买入。\n"
    "   - 谨慎使用“加仓”：仅在趋势极强 (`is_momentum_buy`=True) 且浮盈 > 5% 时加仓。\n"
    "- **卖出**：\n"
    "   - A股为 T+1 制度。只能卖出持仓时间 >= 1天的股票。\n"
    "   - 若趋势破坏（收盘 < EMA20）：必须清仓以保护本金。\n"
    "\n"
    "*** 输出 ***\n"
    "请先提供一段简洁的中文“分析理由 (reasoning)”，解释你对指标的判断，随后输出 JSON 决策。"
    + JSON_FORMAT_INSTRUCTIONS
)

def compute_strategy_flags(market_data: Dict[str, Any]) -> Dict[str, bool]:
    """在 Python 侧预计算策略布尔标志，供 LLM 直接权衡。"""
    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    # 1. 基础数据提取
    price = _to_float(market_data.get('current_price'))
    ema20 = _to_float(market_data.get('current_close_20_ema'))
    rsi6 = _to_float(market_data.get('factor_rsi_6'))
    rsi12 = _to_float(market_data.get('factor_rsi_12'))
    boll_upper = _to_float(market_data.get('factor_boll_upper'))
    boll_lower = _to_float(market_data.get('factor_boll_lower'))
    # 新增：成交量与涨跌幅数据
    vol_curr = _to_float(market_data.get('factor_vol'))
    pct_curr = _to_float(market_data.get('factor_pct_change'))
    today_change_pct = _to_float(market_data.get('today_change_pct'))

    # 2. 序列指标计算
    macd_hist_series = (
        market_data.get('factor_series_macd')
        or market_data.get('macd_hist_array')
        or []
    )
    hist_last = _to_float(macd_hist_series[-1]) if len(macd_hist_series) >= 1 else None
    hist_prev = _to_float(macd_hist_series[-2]) if len(macd_hist_series) >= 2 else None
    hist_prev2 = _to_float(macd_hist_series[-3]) if len(macd_hist_series) >= 3 else None
    
    macd_hist_rising = (hist_last is not None and hist_prev is not None and hist_last > hist_prev)
    macd_hist_positive = (hist_last is not None and hist_last > 0)
    macd_hist_rising_2bars = (
        hist_last is not None and hist_prev is not None and hist_prev2 is not None and
        (hist_prev > hist_prev2) and (hist_last > hist_prev)
    )

    # 3. 计算近窗均量
    try:
        vol_series = market_data.get('factor_series_vol') or []
        vs = [ _to_float(x) for x in vol_series ]
        vs = [ x for x in vs if x is not None ]
        avg_vol_30 = (sum(vs[-30:]) / max(1, len(vs[-30:]))) if vs else None
    except Exception:
        avg_vol_30 = None

    # 4. 基础逻辑判定
    recent_10 = market_data.get('recent_10_closes') or []
    ema20_arr = market_data.get('ema_20_array') or []
    close_above_ema20_2d = False
    try:
        if len(recent_10) >= 2 and len(ema20_arr) >= 2:
            c_last = _to_float(recent_10[-1])
            c_prev = _to_float(recent_10[-2])
            e_last = _to_float(ema20_arr[-1])
            e_prev = _to_float(ema20_arr[-2])
            if None not in (c_last, c_prev, e_last, e_prev):
                close_above_ema20_2d = (c_last > e_last) and (c_prev > e_prev)
    except Exception:
        close_above_ema20_2d = False

    mean_rev_disabled = False
    try:
        mean_rev_disabled = (
            (price is not None and ema20 is not None and price < ema20) and
            (hist_last is not None and hist_prev is not None and hist_last < hist_prev and hist_last < 0)
        )
    except Exception:
        mean_rev_disabled = False

    # 5. 核心策略标志
    is_trend_buy_strict = (
        macd_hist_positive and macd_hist_rising and close_above_ema20_2d and (rsi12 is not None and rsi12 >= 55.0)
    )
    is_exploratory_buy = (
        (not macd_hist_positive) and macd_hist_rising and
        (price is not None and ema20 is not None and price > ema20) and
        (rsi12 is not None and rsi12 >= 50.0)
    )
    is_mean_reversion_buy = (
        (price is not None and boll_lower is not None and price <= boll_lower * 1.01) and
        (rsi6 is not None and rsi6 <= 30.0) and
        (not mean_rev_disabled)
    )
    is_super_trend = (
        (price is not None and ema20 is not None and price > ema20) and
        (rsi6 is not None and rsi6 >= 65.0) and
        macd_hist_positive
    )
    is_extreme_overbought = (
        (price is not None and boll_upper is not None and price >= (boll_upper * 1.02)) and
        (rsi6 is not None and rsi6 >= 85.0)
    )
    is_momentum_buy = (
        macd_hist_positive and macd_hist_rising and
        (rsi12 is not None and rsi12 > 50.0 and rsi12 < 80.0)
    )
    
    is_overbought_sell = False 
    
    is_trend_invalidation_sell = (
        (hist_last is not None and hist_prev is not None and hist_last < hist_prev) and
        (price is not None and ema20 is not None and price < ema20)
    )
    is_in_downtrend_cap = (
        (price is not None and ema20 is not None and price < ema20)
    )
    is_in_buy_cooldown = bool(market_data.get('buy_cooldown', False))

    close_near_ema20_1pct = (
        price is not None and ema20 is not None and ema20 > 0 and (abs(price/ema20 - 1.0) <= 0.01)
    )

    is_cooldown_release_met = False
    try:
        if (rsi6 is not None and rsi6 < 40.0):
            is_cooldown_release_met = True
        if (price is not None and ema20 is not None):
            if (price >= ema20) and (price <= ema20 * 1.015):
                is_cooldown_release_met = True
    except Exception:
        is_cooldown_release_met = False

    return {
        'is_trend_buy_strict': bool(is_trend_buy_strict),
        'is_exploratory_buy': bool(is_exploratory_buy),
        'is_mean_reversion_buy': bool(is_mean_reversion_buy),
        'is_overbought_sell': bool(is_overbought_sell),
        'is_extreme_overbought': bool(is_extreme_overbought),
        'is_momentum_buy': bool(is_momentum_buy),
        'is_super_trend': bool(is_super_trend),
        'is_trend_invalidation_sell': bool(is_trend_invalidation_sell),
        'is_in_downtrend_cap': bool(is_in_downtrend_cap),
        'is_in_buy_cooldown': bool(is_in_buy_cooldown),
        'macd_hist_rising_2bars': bool(macd_hist_rising_2bars),
        'close_near_ema20_1pct': bool(close_near_ema20_1pct),
        'bull_trap_disabled': False, # Disabled legacy feature
        'bear_trap_disabled': False, # Disabled legacy feature
        'is_cooldown_release_met': bool(is_cooldown_release_met),
    }

def _fmt_number(value: Any, decimals: int = 2) -> str:
    try:
        if value is None:
            return "N/A"
        if isinstance(value, float) and math.isnan(value):
            return "N/A"
        fmt = f"{value:.{decimals}f}"
        return fmt
    except Exception:
        return str(value)


def portfolio_to_string(portfolio_json: Dict[str, Any], symbol: str = None) -> str:
    """Convert portfolio JSON to a concise, human‑readable summary."""
    result_string = "【账户资金与持仓状态】\n"

    timestamp = portfolio_json.get('timestamp')
    if timestamp:
        result_string += f"时间: {timestamp}\n"

    initial_cash = float(portfolio_json.get('initial_cash', 0) or 0)
    total_asset = float(portfolio_json.get('total_asset', 0) or 0)
    available_cash = float(portfolio_json.get('available_cash', 0) or 0)
    total_pnl = float(portfolio_json.get('total_pnl', 0) or 0)

    total_return_pct = (100.0 * (total_asset - initial_cash) / initial_cash) if initial_cash > 0 else 0.0

    result_string += f"当前总收益率: {_fmt_number(total_return_pct, 2)}%\n"
    result_string += f"可用现金: {_fmt_number(available_cash, 2)}\n"
    result_string += f"账户总值: {_fmt_number(total_asset, 2)}\n"
    result_string += f"总浮动盈亏: {_fmt_number(total_pnl, 2)}\n"
    result_string += "当前持仓详情:\n\n"

    positions = portfolio_json.get('positions', []) or []
    if not positions:
        result_string += "(当前无持仓)\n"
        return result_string

    for pos in positions:
        sym = pos.get('symbol', 'N/A')
        qty = float(pos.get('quantity', 0) or 0)
        entry = float(pos.get('entry_price', 0) or 0)
        current = float(pos.get('current_price', 0) or 0)
        pnl = float(pos.get('unrealized_pnl', 0) or 0)
        lev = pos.get('leverage', 1)
        notional = float(pos.get('notional_usd', 0) or 0)
        risk_usd = float(pos.get('risk_usd', 0) or 0)
        confidence = pos.get('confidence', None)
        
        # Calculate individual return percentage
        ret_pct = 0.0
        if entry > 0:
            ret_pct = (current - entry) / entry * 100.0

        line = (
            f"代码: {sym}, "
            f"持仓(手): {_fmt_number(qty / 100.0, 2)} ({_fmt_number(qty, 0)}股), "
            f"成本价: {_fmt_number(entry, 2)}, "
            f"当前价: {_fmt_number(current, 2)}, "
            f"浮盈: {_fmt_number(pnl, 2)} ({_fmt_number(ret_pct, 2)}%), "
            f"市值: {_fmt_number(notional, 2)}"
        )
        result_string += line + "\n"

    return result_string


def market_data_to_string_for_symbol(market_data: Dict[str, Any], symbol: str) -> str:
    """Format a single symbol's market data to a concise, readable string."""

    def _fmt_series(series, decimals=3):
        cleaned = []
        for v in series or []:
            if v is None:
                continue
            if isinstance(v, float) and math.isnan(v):
                continue
            cleaned.append(f"{v:.{decimals}f}")
        return ', '.join(cleaned)

    freq_map = {
        '1m': '1-minute',
        '3m': '3-minute',
        '5m': '5-minute',
        '15m': '15-minute',
        '30m': '30-minute',
        '1h': 'hourly',
        '4h': '4-hour',
        '1d': 'daily'
    }

    symbol_upper = str(symbol).upper()
    intraday = market_data or {}
    frequency = intraday.get('frequency', '1d')
    interval_desc = freq_map.get(frequency, frequency)

    price = intraday.get('current_price')
    ema10 = intraday.get('current_ema10')
    ema20 = intraday.get('current_close_20_ema')
    ma5 = intraday.get('current_ma5')
    ma10 = intraday.get('current_ma10')
    ma20 = intraday.get('current_ma20')
    ma60 = intraday.get('current_ma60')
    
    # 对齐数据源：优先使用 stk_factor 提供的 MACD/RSI
    macd_dif = intraday.get('factor_macd_dif', intraday.get('current_macd_dif') or intraday.get('current_macd'))
    macd_dea = intraday.get('factor_macd_dea', intraday.get('current_macd_dea'))
    macd_hist = intraday.get('factor_macd', intraday.get('current_macd_hist'))
    rsi6 = intraday.get('factor_rsi_6')
    rsi12 = intraday.get('factor_rsi_12')
    rsi24 = intraday.get('factor_rsi_24')
    oi_latest = intraday.get('open_interest_latest')
    oi_avg = intraday.get('open_interest_average')
    funding = intraday.get('funding_rate')

    mid_prices_str = _fmt_series(intraday.get('mid_prices'), 2)
    ema20_array_raw = intraday.get('ema_20_array')
    ema_20_str = _fmt_series(ema20_array_raw, 3)
    macd_dif_series = intraday.get('factor_series_macd_dif') or intraday.get('macd_dif_array') or intraday.get('macd_array')
    macd_dea_series = intraday.get('factor_series_macd_dea') or intraday.get('macd_dea_array')
    macd_hist_series = intraday.get('factor_series_macd') or intraday.get('macd_hist_array')
    macd_dif_str = _fmt_series(macd_dif_series, 3)
    macd_dea_str = _fmt_series(macd_dea_series, 3)
    macd_hist_str = _fmt_series(macd_hist_series, 3)
    rsi6_series = intraday.get('factor_series_rsi_6')
    rsi12_series = intraday.get('factor_series_rsi_12')
    rsi24_series = intraday.get('factor_series_rsi_24')
    rsi_6_str = _fmt_series(rsi6_series, 3)
    rsi_12_str = _fmt_series(rsi12_series, 3)
    rsi_24_str = _fmt_series(rsi24_series, 3)
    recent_10_vals = intraday.get('recent_10_closes') or []
    recent_30_vals = intraday.get('recent_30_closes') or []
    recent_vol_vals = intraday.get('recent_vol') or []
    recent_10_str = _fmt_series(recent_10_vals, 2)
    recent_30_str = _fmt_series(recent_30_vals, 2)
    recent_vol_str = _fmt_series(recent_vol_vals, 0)
    
    # 近30日特征：斜率与波动率（简单特征，便于模型参考）
    slope_30_pct = None
    vol_30_pct = None
    try:
        if isinstance(recent_30_vals, list) and len(recent_30_vals) >= 2:
            a = float(recent_30_vals[0])
            b = float(recent_30_vals[-1])
            if a != 0:
                slope_30_pct = 100.0 * (b - a) / a
            m = sum(float(x) for x in recent_30_vals) / len(recent_30_vals)
            if m != 0:
                var = sum((float(x) - m) ** 2 for x in recent_30_vals) / len(recent_30_vals)
                std = math.sqrt(var)
                vol_30_pct = 100.0 * (std / m)
    except Exception:
        slope_30_pct = None
        vol_30_pct = None
    # 生成派生审计标志，帮助模型识别关键态势（不改变原数据）
    derived_flags = []
    try:
        close_above_ema20_2d = None
        if isinstance(recent_10_vals, list) and isinstance(ema20_array_raw, list) and len(recent_10_vals) >= 2 and len(ema20_array_raw) >= 2:
            c_last = float(recent_10_vals[-1])
            c_prev = float(recent_10_vals[-2])
            e_last = float(ema20_array_raw[-1])
            e_prev = float(ema20_array_raw[-2])
            close_above_ema20_2d = (c_last > e_last) and (c_prev > e_prev)
        macd_hist_up = None
        macd_hist_positive = None
        if isinstance(macd_hist_series, list) and len(macd_hist_series) >= 2:
            h_last = float(macd_hist_series[-1])
            h_prev = float(macd_hist_series[-2])
            macd_hist_up = h_last > h_prev
            macd_hist_positive = h_last > 0
        boll_upper = intraday.get('factor_boll_upper')
        overbought_state = None
        if (boll_upper is not None) and (rsi6 is not None) and (price is not None):
            try:
                overbought_state = (float(price) >= float(boll_upper)) and (float(rsi6) >= 70.0)
            except Exception:
                overbought_state = None
        derived_flags.append(f"derived_flags: macd_hist_up={macd_hist_up} | macd_hist_positive={macd_hist_positive} | close_above_ema20_2d={close_above_ema20_2d} | overbought={overbought_state}")
    except Exception:
        pass

    lines = [
        f"ALL {symbol_upper} DATA",
        f"current_price = {_fmt_number(price, 3)}",
        f"Moving Averages: MA5={_fmt_number(ma5, 2)}, MA10={_fmt_number(ma10, 2)}, EMA10={_fmt_number(ema10, 2)}, MA20={_fmt_number(ma20, 2)}, EMA20={_fmt_number(ema20, 2)}, MA60={_fmt_number(ma60, 2)}",
        f"current_macd_dif = {_fmt_number(macd_dif, 3)}, current_macd_dea = {_fmt_number(macd_dea, 3)}, current_macd_hist = {_fmt_number(macd_hist, 3)}",
        f"RSI(6/12/24) current = {_fmt_number(rsi6, 3)} / {_fmt_number(rsi12, 3)} / {_fmt_number(rsi24, 3)}",
        f"Open Interest: Latest: {_fmt_number(oi_latest, 2)}  Average: {_fmt_number(oi_avg, 2)}",
        f"Funding Rate: {_fmt_number(funding, 6)}",
        f"Intraday series ({interval_desc} intervals, oldest → latest):",
        f"{symbol_upper} mid prices (daily closes): [{mid_prices_str}]",
        (f"{symbol_upper} recent 30 closes: [{recent_30_str}]" if recent_30_str else ""),
        (f"{symbol_upper} recent 30 volume: [{recent_vol_str}]" if recent_vol_str else ""),
        (f"recent_30 features: slope={_fmt_number(slope_30_pct, 2)}% | vol={_fmt_number(vol_30_pct, 2)}%" if (slope_30_pct is not None or vol_30_pct is not None) else ""),
        (f"{symbol_upper} recent 10 closes: [{recent_10_str}]" if recent_10_str else ""),
        f"EMA indicators (20‑period): [{ema_20_str}]",
        f"MACD DIF: [{macd_dif_str}]",
        (f"MACD DEA: [{macd_dea_str}]" if macd_dea_str else ""),
        (f"MACD Histogram: [{macd_hist_str}]" if macd_hist_str else ""),
        f"RSI indicators (6‑Period): [{rsi_6_str}]",
        f"RSI indicators (12‑Period): [{rsi_12_str}]",
        f"RSI indicators (24‑Period): [{rsi_24_str}]",
    ]
    if derived_flags:
        lines.append("Decision audit helpers (derived):")
        for x in derived_flags:
            lines.append(f" - {x}")

    # Provided stk_factor indicators (if present)
    factor_pairs = [
        ("macd", market_data.get('factor_macd')),
        ("macd_dif", market_data.get('factor_macd_dif')),
        ("macd_dea", market_data.get('factor_macd_dea')),
        ("rsi_6", market_data.get('factor_rsi_6')),
        ("rsi_12", market_data.get('factor_rsi_12')),
        ("rsi_24", market_data.get('factor_rsi_24')),
        ("kdj_k", market_data.get('factor_kdj_k')),
        ("kdj_d", market_data.get('factor_kdj_d')),
        ("kdj_j", market_data.get('factor_kdj_j')),
        ("boll_upper", market_data.get('factor_boll_upper')),
        ("boll_mid", market_data.get('factor_boll_mid')),
        ("boll_lower", market_data.get('factor_boll_lower')),
        ("cci", market_data.get('factor_cci')),
        ("pct_change", market_data.get('factor_pct_change')),
    ]
    if any(v is not None for _, v in factor_pairs):
        lines.append("Provided factor indicators (stk_factor current values):")
        for name, val in factor_pairs:
            if val is not None:
                lines.append(f" - {name}: {_fmt_number(val, 4)}")

    return "\n".join(lines)


def _safe_json_parse(text: str) -> Dict[str, Any]:
    """
    Ultra-robust JSON parser for LLM outputs.
    Handles standard JSON (double quotes), Python dicts (single quotes), 
    and noisy text (markdown blocks, extra words).
    """
    if not text:
        return {}

    import json
    import ast
    import re

    # Helper: Try parsing a string with multiple methods
    def try_parse(candidate: str) -> Dict[str, Any]:
        # 1. Standard JSON
        try:
            return json.loads(candidate)
        except:
            pass
        
        # 2. Python Literal (Single quotes)
        try:
            return ast.literal_eval(candidate)
        except:
            pass
            
        # 3. Relaxed fix: Replace single quotes with double quotes (risky but sometimes works)
        try:
            return json.loads(candidate.replace("'", '"'))
        except:
            pass
            
        return None

    # 1. Direct parse attempt
    res = try_parse(text)
    if res is not None and isinstance(res, dict):
        return res

    # 2. Extract JSON block using Regex (Find largest {...} block)
    # Matches { ... } including nested braces (up to a reasonable depth or simple nesting)
    # Simple greedy match from first { to last }
    match = re.search(r'(\{.*\})', text, re.DOTALL)
    if match:
        candidate = match.group(1)
        res = try_parse(candidate)
        if res is not None and isinstance(res, dict):
            return res

    # 3. Markdown block fallback
    match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        candidate = match.group(1)
        res = try_parse(candidate)
        if res is not None and isinstance(res, dict):
            return res

    return {}


def analyze_market_features(market_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Python 负责算数：计算复杂的布尔逻辑，减轻 LLM 的计算负担。
    生成可读的趋势、突破、动能信号。
    """
    price = market_data.get('current_price')
    ema10 = market_data.get('current_ema10')
    ema20 = market_data.get('current_close_20_ema')
    ema60 = market_data.get('current_ema60')
    
    macd_hist = market_data.get('factor_macd') or 0
    macd_slope = market_data.get('macd_hist_slope') or 0
    
    # 优先使用 stk_factor 的指标
    rsi6 = market_data.get('factor_rsi_6')
    boll_upper = market_data.get('factor_boll_upper') or market_data.get('current_boll_upper')

    features = {
        "trend_label": "Unknown",
        "is_super_trend": False,
        "is_breakout": False,
        "momentum_status": "Neutral",
        "risk_warning": "None"
    }

    # 1. 判定趋势状态 (Super Trend)
    # 逻辑：价格 > EMA10 > EMA20，且 MACD > 0，且 RSI 强势 (>60)
    if price and ema10 and ema20:
        if price > ema10 and ema10 > ema20:
            if macd_hist > 0:
                features["is_super_trend"] = True
                features["trend_label"] = "Super Bullish (Strong Uptrend)"
            else:
                features["trend_label"] = "Bullish (Retracement/Weak)"
        elif price < ema20:
            if ema60 and price < ema60:
                features["trend_label"] = "Bearish (Downtrend)"
            else:
                features["trend_label"] = "Bearish (Short term)"
        else:
            features["trend_label"] = "Bullish (Normal)"
    
    # 2. 判定突破 (Breakout) - 解决张江高科踏空的关键
    # 逻辑：价格 > 布林上轨，且 MACD 在加速扩张 (Slope > 0)
    if price and boll_upper and price >= boll_upper * 0.995: # 接近或突破
        features["is_breakout"] = True

    # 3. 判定动能
    if macd_slope > 0 and macd_hist > 0:
        features["momentum_status"] = "Expanding (Strong Buy Force)"
    elif macd_slope < 0 and macd_hist > 0:
        features["momentum_status"] = "Fading (Bullish Divergence Risk)"
    elif macd_slope < 0 and macd_hist < 0:
        features["momentum_status"] = "Accelerating Down (Strong Sell Force)"
    elif macd_slope > 0 and macd_hist < 0:
        features["momentum_status"] = "Recovering (Possible Reversal)"

    # 4. 风险提示
    if rsi6 and rsi6 > 85 and not features["is_super_trend"]:
        features["risk_warning"] = "EXTREME OVERBOUGHT (RSI>85). Risk of pullback."
    elif rsi6 and rsi6 < 20:
        features["risk_warning"] = "EXTREME OVERSOLD. Watch for bounce."
        
    return features

def build_market_prompt(symbol: str, market_data: Dict[str, Any], portfolio_json: Dict[str, Any]) -> str:
    md_str = market_data_to_string_for_symbol(market_data, symbol)
    pf_str = portfolio_to_string(portfolio_json, symbol)
    
    # ... State extraction ...
    state = market_data.get('llm_state') or {}
    # ... (Keep logic) ...
    has_position = bool(state.get('has_position', False))
    is_first_trade = bool(state.get('is_first_trade', False))
    last_action = str(state.get('last_action', 'none'))
    allowed_actions = state.get('allowed_actions', ['buy', 'hold'])
    lot_size = int(state.get('lot_size', 100))
    min_lot_count = int(state.get('min_lot_count', 1))
    tplus1_sell_available = bool(state.get('tplus1_sell_available_today', False))
    available_cash = state.get('available_cash')
    current_price = state.get('current_price')
    max_buyable_lots = state.get('max_buyable_lots')
    max_sellable_lots = state.get('max_sellable_lots')
    default_position_fraction = state.get('default_position_fraction', 0.25)
    avg_entry_price = state.get('avg_entry_price', None)
    recent_actions_text = state.get('recent_actions_text', None)

    rules_block = (
        f"【A股交易规则与账户状态】（请严格遵守）：\n"
        f"- **方向**：仅允许做多（Long only）。卖出指平仓。\n"
        f"- **T+1 状态**：{'今日可卖' if tplus1_sell_available else '今日冻结(T+1限制)'}。\n"
        f"- **单位**：1手 = {lot_size}股。买卖必须是整数手。\n"
        f"- **账户**：持仓状态={has_position}, 资金={available_cash}。\n"
        f"- **今日允许动作**：{allowed_actions}。\n"
    )
    recent_block = ""
    if recent_actions_text:
        recent_block = f"\n【最近交易记录】:\n{recent_actions_text}\n"

    # === 新增：计算高级特征并生成“胆量包”指令 ===
    feats = analyze_market_features(market_data)
    
    quant_signal_block = (
        f"\n【高级量化信号参考 (Python Calculated)】\n"
        f"- 趋势状态 (Trend Status): {feats['trend_label']}\n"
        f"- 动能状态 (Momentum): {feats['momentum_status']}\n"
        f"- 关键信号 (Key Signals):\n"
        f"  * SUPER TREND: {'YES' if feats['is_super_trend'] else 'NO'} "
        f"(若 YES: 忽略 RSI 超买，坚决持有。若无仓位，可追涨。)\n"
        f"  * BREAKOUT: {'YES' if feats['is_breakout'] else 'NO'} "
        f"(若 YES: 忽略 RSI 高位，这是强力突破信号。)\n"
        f"- 风险提示: {feats['risk_warning']}\n"
        f"\n【战术执行指南 (ACTION GUIDE)】\n"
        f"1. 如果 `BREAKOUT` 为 YES 且无持仓：**立即买入 (BUY NOW)**。不要等待回调 (Do NOT wait for dip)。不要害怕 RSI > 80。\n"
        f"2. 如果 `SUPER TREND` 为 YES：持有为主。若想加仓，可等待小幅回调或直接突破买入。\n"
    )

    return f'''\n        {md_str}\n{quant_signal_block}\n        {pf_str}\n{recent_block}\n        {rules_block}\n        '''

def trade_decision_provider(market_data_dict: Dict[str, Dict[str, Any]], portfolio_json: Dict[str, Any], model_name: str = None, strategy_prompt: str = None) -> Dict[str, Any]:
    """
    根据市场数据与组合信息生成各标的的交易决策。
    返回：字典，key 为 symbol，value 为模型返回的对象（包含 trade_signal_args 与 reasoning）。
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY 环境变量。")
    decisions: Dict[str, Any] = {}
    # 选择模型：入参优先，其次环境变量，默认 deepseek-chat
    selected_model = (model_name or LLM_MODEL_ENV or "deepseek-chat").strip()
    
    # Determine System Prompt
    if strategy_prompt and strategy_prompt.strip():
        # Inject custom strategy but append JSON format rules to ensure stability
        SYSTEM_PROMPT = strategy_prompt + "\n" + JSON_FORMAT_INSTRUCTIONS
    else:
        SYSTEM_PROMPT = SYSTEM_PROMPT_TEXT

    for symbol, market_data in (market_data_dict or {}).items():
        # Extract state safely from market_data
        try:
            llm_state = market_data.get('llm_state') or {}
        except Exception:
            llm_state = {}
        
        tplus1_sell_available = bool(llm_state.get('tplus1_sell_available_today', False))
        max_sellable_lots = int(llm_state.get('max_sellable_lots', 0) or 0)
        # 补充提取 max_buyable_lots，防止后续未定义错误
        max_buyable_lots = int(llm_state.get('max_buyable_lots', 0) or 0)
        available_cash = float(llm_state.get('available_cash', 0.0) or 0.0)
        lot_size = int(llm_state.get('lot_size', 100) or 100)
        allowed_actions = llm_state.get('allowed_actions', ['buy', 'hold'])

        MARKET_PROMPT = build_market_prompt(symbol, market_data, portfolio_json)
        # 直接使用 DeepSeek HTTP API；保持接口与输出不变，并加入模型不可用回退
        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": selected_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": MARKET_PROMPT}
            ],
        }

        def _post_with_retry(model: str, max_retries: int = 3):
            payload["model"] = model
            last_error = None
            for attempt in range(max_retries):
                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=180)
                    if resp.status_code == 200:
                        return resp.json()
                    
                    # Handle specific errors that might not need retry or need specific handling
                    # DeepSeek returns 400 for invalid model
                    err_text = resp.text
                    if resp.status_code == 400 and ("Model Not Exist" in err_text or "model_not_found" in err_text or "invalid_request_error" in err_text):
                         raise ValueError("Model Not Exist") # Signal to switch model

                    print(f"[DeepSeek] Error {resp.status_code}: {err_text[:100]}..., retrying ({attempt + 1}/{max_retries})...")
                    last_error = RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text}")
                
                except requests.RequestException as e:
                    print(f"[DeepSeek] Network error: {e}, retrying ({attempt + 1}/{max_retries})...")
                    last_error = e
                except ValueError as e:
                    raise e # Re-raise model error immediately
                
                if attempt < max_retries - 1:
                    time.sleep(2 * (attempt + 1)) # Exponential backoff: 2, 4, 6s
            
            raise last_error or RuntimeError(f"DeepSeek API failed after {max_retries} retries.")

        try:
            data = _post_with_retry(selected_model)
        except ValueError:
            # Fallback for model not found
            if selected_model != "deepseek-chat":
                print(f"[DeepSeek] Model {selected_model} not found, falling back to deepseek-chat")
                selected_model = "deepseek-chat"
                data = _post_with_retry(selected_model)
            else:
                raise

        message = ((data.get("choices") or [{}])[0].get("message") or {})
        content = message.get("content") or ""
        reasoning = message.get("reasoning_content")

        # 解析模型输出为 JSON
        result = _safe_json_parse(content)

        # 尝试读取标准键 trade_signal_args
        args = result.get("trade_signal_args")
        if not isinstance(args, dict):
            # 兼容：模型直接返回扁平 JSON（不含 trade_signal_args 包裹）
            # 识别若存在常见参数键，则将其包裹为 trade_signal_args
            flat_keys = {k.lower() for k in (result.keys() if isinstance(result, dict) else [])}
            has_flat_structure = any(k in flat_keys for k in ["signal", "action"]) and ("quantity" in flat_keys)
            if has_flat_structure:
                try:
                    # 构造兼容参数，尽量保留原值，缺失时兜底
                    sig = result.get("signal") or result.get("action") or "hold"
                    qty = float(result.get("quantity", 0) or 0)
                    entry_price = result.get("entry_price")
                    if entry_price is None:
                        # 兜底：使用当前价
                        md = market_data
                        entry_price = md.get("current_price")
                    lev = float(result.get("leverage", 1.0) or 1.0)
                    conf = float(result.get("confidence", 0.5) or 0.5)
                    pt = result.get("profit_target")
                    sl = result.get("stop_loss")
                    sym = result.get("symbol") or symbol
                    args = {
                        "symbol": sym,
                        "signal": str(sig).lower(),
                        "quantity": qty,
                        "entry_price": entry_price,
                        "leverage": lev,
                        "confidence": conf,
                        "profit_target": pt,
                        "stop_loss": sl,
                    }
                    result = {"trade_signal_args": args}
                    print("[WARN] 模型输出未包含 trade_signal_args，已按扁平 JSON 自动兼容包裹。\n")
                except Exception:
                    args = None
            if not isinstance(args, dict):
                # 兜底：输出 hold，保证回测不中断
                md = market_data or {}
                fallback_args = {
                    "symbol": symbol,
                    "signal": "hold",
                    "quantity": 0,
                    "entry_price": md.get("current_price"),
                    "leverage": 1.0,
                    "confidence": 0.5,
                    "profit_target": None,
                    "stop_loss": None,
                }
                result = {"trade_signal_args": fallback_args}
                print("[WARN] 模型输出无法解析为有效 JSON，使用安全兜底：hold。\n")

        # 统一规范化与约束检查：确保信号与手数可执行、键完整
        if isinstance(args, dict):
            
            # 信号与手数规范化
            sig = str(args.get('signal', args.get('action', 'hold')) or 'hold').lower().strip()
            if sig in ('long', 'buy_open', 'open_long'):
                sig = 'buy'
            elif sig in ('short', 'sell_open', 'open_short'):
                sig = 'sell'
            elif sig in ('wait', 'stay', 'idle', 'nop'):
                sig = 'hold'

            # 若信号不在允许集合，直接改为 hold
            if sig not in allowed_actions:
                sig = 'hold'
            
            qty_lots = int(float(args.get('quantity', 0) or 0))
            
            # Entry Price Handling (Default to current price if missing)
            entry_price = args.get('entry_price')
            if entry_price is None:
                try:
                    entry_price = float((market_data.get('current_price') or 0))
                except Exception:
                    entry_price = 0.0
            entry_price = float(entry_price or 0)

            # Default rates (Standard A-share rates)
            commission_rate = 0.0003
            transfer_fee_rate = 0.00001
            is_shanghai = str(symbol).startswith('6')

            # --- 核心风控与 A 股规则 (Hard Rules Only) ---
            # 移除所有 Python 侧的策略干预 (Technical checks, Cooldowns, Caps)
            # 仅保留资金、持仓、T+1 限制

            if sig == 'buy':
                try:
                    md_local = (market_data_dict.get(symbol) or {})
                    # 仅保留基础冷却检查作为熔断器
                    in_cooldown = bool(md_local.get('buy_cooldown', False))
                    # 如果在冷却期，但 LLM 仍坚持买入，我们选择放行（假设它看到了 Breakout）
                    # 除非你需要强制冷却，否则这里不做拦截
                    pass
                except Exception:
                    pass

                # === 移除所有基于旧 flags 的硬性拦截 ===
                # 我们现在完全信任 LLM 基于 analyze_market_features 生成的决策。
                
                # 资金上限约束 (Financial Constraint) - 必须保留
                if max_buyable_lots >= 0 and qty_lots > max_buyable_lots:
                    qty_lots = max_buyable_lots

                # 最小手数约束
                if qty_lots < 1:
                    qty_lots = 0
                    sig = 'hold'            
            elif sig in ('sell', 'close'):
                # T+1 与持仓约束
                if not tplus1_sell_available:
                    sig = 'hold'
                    qty_lots = 0
                else:
                    if sig == 'close':
                        qty_lots = max_sellable_lots
                    else:
                        if qty_lots > max_sellable_lots:
                            qty_lots = max_sellable_lots
                        if qty_lots < 1:
                            sig = 'hold'
                            qty_lots = 0
            else:
                # Hold
                sig = 'hold'
                qty_lots = 0

            # Limit Price Logic
            limit_price = args.get('limit_price')
            try:
                current_p = float((market_data.get('current_price') or 0))
                is_price_valid = (limit_price is not None and float(limit_price) > 0)
                if is_price_valid:
                    if current_p > 0 and abs(float(limit_price) - current_p) / current_p > 0.10:
                        is_price_valid = False
                if not is_price_valid and current_p > 0:
                    if sig == 'buy':
                        limit_price = current_p * 1.015
                    elif sig in ('sell', 'close'):
                        limit_price = current_p * 0.985
                    else:
                        limit_price = 0.0
                limit_price = round(float(limit_price), 2) if limit_price is not None else None
            except Exception:
                limit_price = None

            # Risk Management Fields
            stop_loss = args.get('stop_loss')
            invalidation_condition = args.get('invalidation_condition')
            if not invalidation_condition:
                try:
                    if stop_loss is not None:
                        invalidation_condition = f"close below {float(stop_loss):.2f}"
                    else:
                        invalidation_condition = "close below EMA20 for 2 consecutive days"
                except Exception:
                    invalidation_condition = "close below EMA20 for 2 consecutive days"

            risk_usd = args.get('risk_usd')
            try:
                if risk_usd is None and (stop_loss is not None) and (entry_price is not None):
                    risk_usd = abs(float(entry_price) - float(stop_loss)) * int(qty_lots) * int(lot_size)
            except Exception:
                pass

            # Final Output Construction
            allowed_keys = {
                'symbol', 'signal', 'quantity', 'entry_price', 'limit_price', 'leverage', 'confidence',
                'invalidation_condition', 'profit_target', 'stop_loss', 'risk_usd',
                'stop_loss_pct', 'tp_trailing_pct'
            }

            if sig == 'hold':
                qty_lots = 0
                args['confidence'] = 0.0
                for k in ['profit_target', 'stop_loss', 'invalidation_condition', 'stop_loss_pct', 'tp_trailing_pct']:
                    if k in args:
                        args.pop(k, None)

            if sig == 'buy':
                if args.get('stop_loss_pct') is None:
                    args['stop_loss_pct'] = 0.05
                if args.get('tp_trailing_pct') is None:
                    args['tp_trailing_pct'] = 0.03

            normalized = {
                'symbol': args.get('symbol') or symbol,
                'signal': sig,
                'quantity': int(qty_lots),
                'entry_price': limit_price if limit_price is not None else entry_price,
                'limit_price': limit_price,
                'leverage': float(args.get('leverage', 1.0) or 1.0),
                'confidence': float(args.get('confidence', 0.5) or 0.5),
                'invalidation_condition': invalidation_condition,
                'risk_usd': risk_usd if risk_usd is not None else args.get('risk_usd'),
                'profit_target': args.get('profit_target'),
                'stop_loss': args.get('stop_loss'),
                'stop_loss_pct': args.get('stop_loss_pct'),
                'tp_trailing_pct': args.get('tp_trailing_pct')
            }
            result['trade_signal_args'] = {k: v for (k, v) in normalized.items() if k in allowed_keys}

        # 附带思考过程与原始文本，供终端/文件审计
        result["reasoning"] = reasoning or ""
        result["_raw_text"] = content
        decisions[symbol] = result

    return decisions
