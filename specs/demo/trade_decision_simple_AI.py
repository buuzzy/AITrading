"""
Trading Decision Provider - Generates trading signals based on market data
"""
from typing import Dict, Any
import json
import math
import os
import requests
import dotenv
dotenv.load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
LLM_MODEL_ENV = os.getenv("LLM_MODEL")

# 模块级：新增 build_market_prompt（导出给 backtest.py 使用）
SYSTEM_PROMPT_TEXT = (
    "You are an A‑share backtesting trading agent.\n"
    "STRICTLY NO FUTURE OR EXTERNAL KNOWLEDGE. Use ONLY the provided data.\n"
    "STRICTLY NO GUESSING: do not infer anything not explicitly provided; do not parse raw time‑series arrays.\n"
    "External technical analysis is OPTIONAL and for summary/audit only; it MUST NOT decide trades when quantitative constraints disagree.\n"
    "If uncertain or constraints are violated, respond HOLD with quantity=0 lots.\n"
    "All decisions must respect A‑share constraints (lot_size, T+1, allowed_actions).\n"
    "Position sizing (AGGRESSIVE BASELINE): baseline quantity(lots) ≈ floor(max_buyable_lots * default_position_fraction), and NEVER below min_lot_count (default=1) if affordable.\n"
    "Confidence‑scaled sizing (UNIFIED): confidence ≥ 0.75 → ≈50% of max_buyable_lots; ~0.5 → ≈25%; ≤0.4 → HOLD or ≤min_lot_count (exploratory only).\n"
    "Cost awareness: max_buyable_lots ALREADY accounts for estimated buy fees (commission + transfer).\n"
    "\n"
    "Two‑tier entry triggers (ATTACK + CONFIRMATION):\n"
    "- Entry A (attack, baseline): close > EMA20; RSI(12) ≥ 50; MACD histogram ≥ 0 → open baseline lots (≥min_lot_count).\n"
    "- Entry B (strict confirmation): after Entry A, further require close > EMA20 for 2 consecutive days AND MACD histogram rising for ≥2 bars → allow medium lots (~50% of max_buyable_lots).\n"
    "\n"
    "Trigger rules (REVISED, risk‑first & simplicity):\n"
    "- BUY (trend, STRICT): MACD histogram > 0 AND rising; close > EMA20 for 2 consecutive days; RSI(12) ≥ 55.\n"
    "- BUY (exploratory, LIMITED): ONLY if MACD histogram < 0 BUT rising AND close > EMA20 AND RSI(12) ≥ 50; at most min_lot_count lots; enforce a 2–3 day cooldown before any further buy unless trend STRICT is met.\n"
    "- BUY (mean‑reversion, STRICT): price ≤ Bollinger lower × 1.01 AND RSI(6) ≤ 30; disabled if (close < EMA20 AND MACD histogram makes a new low).\n"
    "- ADD‑ON only on pullbacks near EMA20, NOT on expansion (no chasing).\n"
    "- SELL/CLOSE (overbought PRIORITY): price ≥ Bollinger upper AND RSI(6) ≥ 70 → SELL/CLOSE takes precedence over any BUY; no new/add buys allowed in this state.\n"
    "- SELL/CLOSE (trend invalidation): MACD histogram turns down AND close < EMA20 → reduce ≥50% and start a 3‑day cooldown; if close < EMA20 for 2 consecutive days → reduce ≥30%, and if MACD histogram also turns down → reduce ≥50%.\n"
    "- HOLD when signals conflict or weak, or when in cooldown.\n"
    "Risk caps (DOWN‑MOMENTUM): when MACD histogram < 0 OR close < EMA20, per‑symbol position cap ≤ 3 lots; prefer reduction/HOLD until trend STRICT is satisfied.\n"
    "Execution rhythm: at most 1 transaction per day; limit additions to ≤2 times in any 5‑day window (including exploratory).\n"
    "Do NOT use all cash and do NOT invent unseen data.\n"
    "Include an invalidation_condition: prefer 'close below stop_loss' if stop_loss is set, otherwise 'close below EMA20 for 2 consecutive days'. When signal=='hold', OMIT optional fields (invalidation_condition/stop_loss/stop_loss_pct/tp_trailing_pct/profit_target)."
)

def compute_strategy_flags(market_data: Dict[str, Any]) -> Dict[str, bool]:
    """在 Python 侧预计算策略布尔标志，供 LLM 直接权衡。
    仅使用末值与简单派生，不深度解析原始长序列。
    """
    def _to_float(x):
        try:
            return float(x)
        except Exception:
            return None

    price = _to_float(market_data.get('current_price'))
    ema20 = _to_float(market_data.get('current_close_20_ema'))
    rsi6 = _to_float(market_data.get('factor_rsi_6'))
    rsi12 = _to_float(market_data.get('factor_rsi_12'))
    boll_upper = _to_float(market_data.get('factor_boll_upper'))
    boll_lower = _to_float(market_data.get('factor_boll_lower'))

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

    # 连续2日 close > EMA20（使用 recent_10 与 ema_20_array 的最后两项）
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

    # 均值回归禁用条件：价<EMA20 且柱转下且为负
    mean_rev_disabled = False
    try:
        mean_rev_disabled = (
            (price is not None and ema20 is not None and price < ema20) and
            (hist_last is not None and hist_prev is not None and hist_last < hist_prev and hist_last < 0)
        )
    except Exception:
        mean_rev_disabled = False

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
    is_overbought_sell = (
        (price is not None and boll_upper is not None and price >= boll_upper) and
        (rsi6 is not None and rsi6 >= 70.0)
    )
    is_trend_invalidation_sell = (
        (hist_last is not None and hist_prev is not None and hist_last < hist_prev) and
        (price is not None and ema20 is not None and price < ema20)
    )
    is_in_downtrend_cap = (
        (hist_last is not None and hist_last < 0) or (price is not None and ema20 is not None and price < ema20)
    )
    # 冷却窗口：默认 False；若上层注入 buy_cooldown=True 则遵循
    is_in_buy_cooldown = bool(market_data.get('buy_cooldown', False))

    close_near_ema20_1pct = (
        price is not None and ema20 is not None and ema20 > 0 and (abs(price/ema20 - 1.0) <= 0.01)
    )

    return {
        'is_trend_buy_strict': bool(is_trend_buy_strict),
        'is_exploratory_buy': bool(is_exploratory_buy),
        'is_mean_reversion_buy': bool(is_mean_reversion_buy),
        'is_overbought_sell': bool(is_overbought_sell),
        'is_trend_invalidation_sell': bool(is_trend_invalidation_sell),
        'is_in_downtrend_cap': bool(is_in_downtrend_cap),
        'is_in_buy_cooldown': bool(is_in_buy_cooldown),
        'macd_hist_rising_2bars': bool(macd_hist_rising_2bars),
        'close_near_ema20_1pct': bool(close_near_ema20_1pct),
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
    result_string = "HERE IS YOUR ACCOUNT INFORMATION & PERFORMANCE\n"

    timestamp = portfolio_json.get('timestamp')
    if timestamp:
        result_string += f"As of: {timestamp}\n"

    initial_cash = float(portfolio_json.get('initial_cash', 0) or 0)
    total_asset = float(portfolio_json.get('total_asset', 0) or 0)
    available_cash = float(portfolio_json.get('available_cash', 0) or 0)
    total_pnl = float(portfolio_json.get('total_pnl', 0) or 0)

    total_return_pct = (100.0 * (total_asset - initial_cash) / initial_cash) if initial_cash > 0 else 0.0

    result_string += f"Current Total Return (percent): {_fmt_number(total_return_pct, 2)}%\n"
    result_string += f"Available Cash: {_fmt_number(available_cash, 2)}\n"
    result_string += f"Current Account Value: {_fmt_number(total_asset, 2)}\n"
    result_string += f"Total Unrealized PnL: {_fmt_number(total_pnl, 2)}\n"
    result_string += "Current live positions & performance:\n\n"

    positions = portfolio_json.get('positions', []) or []
    if not positions:
        result_string += "(No open positions)\n"
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

        line = (
            f"Symbol: {sym}, "
            f"Qty(shares): {_fmt_number(qty, 4)}, "
            f"Entry: {_fmt_number(entry, 2)}, "
            f"Current: {_fmt_number(current, 2)}, "
            f"PnL: {_fmt_number(pnl, 2)}, "
            f"Notional: {_fmt_number(notional, 2)}, "
            f"Risk: {_fmt_number(risk_usd, 2)}, "
            f"Leverage: {lev}x"
        )
        if confidence is not None:
            line += f", Confidence: {_fmt_number(float(confidence), 2)}"
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
    ema20 = intraday.get('current_close_20_ema')
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
    recent_10_str = _fmt_series(recent_10_vals, 2)
    recent_30_str = _fmt_series(recent_30_vals, 2)
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
        f"current_price = {_fmt_number(price, 3)}, current_ema20 = {_fmt_number(ema20, 3)}, current_macd_dif = {_fmt_number(macd_dif, 3)}, current_macd_dea = {_fmt_number(macd_dea, 3)}, current_macd_hist = {_fmt_number(macd_hist, 3)}",
        f"RSI(6/12/24) current = {_fmt_number(rsi6, 3)} / {_fmt_number(rsi12, 3)} / {_fmt_number(rsi24, 3)}",
        f"Open Interest: Latest: {_fmt_number(oi_latest, 2)}  Average: {_fmt_number(oi_avg, 2)}",
        f"Funding Rate: {_fmt_number(funding, 6)}",
        f"Intraday series ({interval_desc} intervals, oldest → latest):",
        f"{symbol_upper} mid prices (daily closes): [{mid_prices_str}]",
        (f"{symbol_upper} recent 30 closes: [{recent_30_str}]" if recent_30_str else ""),
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
    ]
    if any(v is not None for _, v in factor_pairs):
        lines.append("Provided factor indicators (stk_factor current values):")
        for name, val in factor_pairs:
            if val is not None:
                lines.append(f" - {name}: {_fmt_number(val, 4)}")

    return "\n".join(lines)


def _safe_json_parse(text: str) -> Dict[str, Any]:
    """
    尝试从模型输出中提取 JSON 对象：
    - 先直接 json.loads
    - 失败则查找首个 '{' 到最后一个 '}' 的片段再解析
    - 若仍失败，返回空字典，保证调用方健壮性
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = text[start:end+1]
            return json.loads(candidate)
        return {}
    except Exception:
        return {}


def build_market_prompt(symbol: str, market_data: Dict[str, Any], portfolio_json: Dict[str, Any]) -> str:
    md_str = market_data_to_string_for_symbol(market_data, symbol)
    pf_str = portfolio_to_string(portfolio_json, symbol)
    ta_text = market_data.get('technical_analysis')

    # 可选：由上层回测注入的“可执行状态”与交易规则
    state = market_data.get('llm_state') or {}
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
        f"A股制度与状态（请严格遵守）：\n"
        f"- 仅允许开多，不允许开空；卖出仅指减仓（signal='sell'）或平仓（signal='close'），不构成做空。\n"
        f"- T+1：当日买入的股票次一交易日才可卖出；今日可卖出：{tplus1_sell_available}.\n"
        f"- 最小交易单位：1手={lot_size}股；买入数量以‘手数’表达，且不得低于{min_lot_count}手（默认=1手）。\n"
        f"- 账户状态：has_position={has_position}, is_first_trade={is_first_trade}, last_action={last_action}.\n"
        f"- 单票可用现金上限：{available_cash}；当前价格：{current_price}；最多可买手数（含买入费用）：{max_buyable_lots}；最多可卖手数：{max_sellable_lots}.\n"
        f"- 今日允许动作集合：{allowed_actions}（仅从该集合中选择一个动作）。\n"
        f"\n风险与仓位指导（统一映射与上限）：\n"
        f"- 基线仓位：默认仓位比例 default_position_fraction={default_position_fraction}；建议手数≈floor(max_buyable_lots * default_position_fraction)。\n"
        f"- 置信度映射（统一）：confidence≥0.75→≈50%；~0.5→≈25%；≤0.4→HOLD/≤1手。\n"
        f"- 动能为负或价<EMA20阶段：单票持仓上限≤3手；优先减仓或 HOLD。\n"
        f"- 严禁一次性用尽全部可用现金，遵守手数与现金约束。\n"
        f"- 当前持仓均价（若有）：{_fmt_number(avg_entry_price, 2)}。\n"
        f"- 统一失效条件建议：若设置了 stop_loss，则 invalidation_condition='close below stop_loss'；否则采用 'close below EMA20 for 2 consecutive days' 并与减仓联动。\n"
        f"\n解析约束（禁止猜测与原始序列解析）：\n"
        f"- 严禁解析 recent_30_closes / recent_10_closes / factor_series_* 数组来推断'上升/创新低'；仅使用已提供的显式字段。\n"
        f"- 若数据不足或存在不一致，请选择 HOLD，并 quantity=0。\n"
        f"\n外部技术分析引用与使用（可选）：\n"
        f"- 外部技术分析文本可用于方向性总结与审计说明，不得单独触发交易。\n"
        f"- 在 Reasoning 开头简要总结其方向性结论（如趋势/支撑/阻力）；若与量化门槛冲突，以量化约束优先并说明取舍理由。\n"
        f"\n输出约束：\n"
        f"- 严禁使用任何未提供的未来或外部信息，不得参考训练知识库或新闻。\n"
        f"- 仅输出一个 JSON 对象，键为 trade_signal_args，结构如下：\n"
        f"  trade_signal_args = {{\n"
        f"    'symbol': '{symbol}',\n"
        f"    'signal': one of {allowed_actions},  # 'sell' 为部分减仓，'close' 为全平\n"
        f"    'quantity': INT lots,  # 若 signal=='buy'，1 <= quantity <= {max_buyable_lots}; 若 signal in ['sell','close']，{('1 <= quantity <= ' + str(max_sellable_lots)) if ('sell' in allowed_actions or 'close' in allowed_actions) else '不可用（今日不可卖出）'}；若 signal=='hold'，quantity=0\n"
        f"    'entry_price': float（可省略；省略时默认使用当前价）,\n"
        f"    'leverage': 1.0,\n"
        f"    'confidence': 0.0~1.0,\n"
        f"    'invalidation_condition': string（建议使用统一失效条件；若 signal=='hold'，请省略该字段及所有可选风险字段）\n"
        f"    'profit_target': optional float,\n"
        f"    'stop_loss': optional float,\n"
        f"    'stop_loss_pct': optional float（建议5%）,\n"
        f"    'tp_trailing_pct': optional float（建议3%）\n"
        f"  }}\n"
        f"- 若不确定或不在允许动作集合内，请输出 hold 并 quantity=0。\n"
        )
    recent_block = ""
    if recent_actions_text:
        recent_block = f"\nRECENT EXECUTIONS (last actions):\n{recent_actions_text}\n"

    corrections_block = (
        "策略修正摘要（需严格遵守）：\n"
        "- 入场两级：入场A（进攻）= close>EMA20 & RSI(12)≥50 & MACD柱≥0，基础仓位≥min_lot_count；入场B（严格确认）= 连续2日close>EMA20 且 MACD柱≥2棒连续上升，允许提升至中等仓位（≈max_buyable_lots的50%）。\n"
        "- 趋势BUY收紧：MACD柱>0且上升；收盘>EMA20连续2日；RSI(12)≥55。\n"
        "- 探索BUY限制：MACD柱<0但上升时，仅允许≤min_lot_count，并强制2–3日冷却；趋势未转正禁止继续加仓。\n"
        "- 超买优先级：价≥上轨且RSI(6)≥70，SELL/CLOSE优先，禁止BUY；分层减仓：RSI(6)∈[70,75)→≥30%减仓，∈[75,80)→≥50%减仓，≥80→平仓。\n"
        "- 失效联动：收盘<EMA20连续2日→减仓≥30%；若同时MACD柱转下→减仓≥50%；并进入3日冷却。\n"
        "- 下跌阶段上限：MACD柱<0或价<EMA20时，总持仓≤3手；倾向减仓或HOLD。\n"
        "- 节奏：单日至多1次交易；5日内加仓≤2次（含探索）；加仓仅允许在EMA20附近回撤（禁止扩张态加仓，‘附近’定义为|price/EMA20−1|≤1%）。\n"
    )

    ta_block = f"\nEXTERNAL TECHNICAL ANALYSIS (workflow):\n{ta_text}\n" if ta_text else ""
    # 预计算策略标志并嵌入提示，简化 LLM 的解析任务
    strategy_flags = compute_strategy_flags(market_data)
    flags_block = (
        "\nSTRATEGY FLAGS (Python 预计算，供直接权衡)：\n"
        f"{json.dumps(strategy_flags, ensure_ascii=False)}\n"
        "优先级规则：\n"
        "- 超买卖出（is_overbought_sell=True）优先级最高；若该动作不在 allowed_actions 中，则选择 HOLD。\n"
        "- 若多信号冲突，请选择 HOLD，并保持 quantity=0。\n"
        "- 所有决策须尊重 allowed_actions 与 T+1 合规；禁止越权。\n"
    )
    return f'''\n        {ta_block}DATA FOR {symbol} (daily, recent 30 trading days):\n        {md_str}\n\n        PORTFOLIO SNAPSHOT:\n        {pf_str}\n{recent_block}\n        BACKTEST STATE & RULES:\n        {rules_block}\n{flags_block}\n        STRATEGY CORRECTIONS:\n        {corrections_block}\n        '''

def trade_decision_provider(market_data_dict: Dict[str, Dict[str, Any]], portfolio_json: Dict[str, Any], model_name: str = None) -> Dict[str, Any]:
    """
    根据市场数据与组合信息生成各标的的交易决策。
    返回：字典，key 为 symbol，value 为模型返回的对象（包含 trade_signal_args 与 reasoning）。
    """
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("缺少 DEEPSEEK_API_KEY 环境变量。")
    decisions: Dict[str, Any] = {}
    # 选择模型：入参优先，其次环境变量，默认 deepseek-chat
    selected_model = (model_name or LLM_MODEL_ENV or "deepseek-chat").strip()
    for symbol, market_data in (market_data_dict or {}).items():
        SYSTEM_PROMPT = SYSTEM_PROMPT_TEXT
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

        def _post_once(model: str):
            payload["model"] = model
            resp = requests.post(url, headers=headers, json=payload, timeout=180)
            if resp.status_code != 200:
                raise RuntimeError(f"DeepSeek API error {resp.status_code}: {resp.text}")
            return resp.json()

        try:
            data = _post_once(selected_model)
        except Exception as e:
            msg = str(e)
            if ("Model Not Exist" in msg or "model_not_found" in msg or "invalid_request_error" in msg) and selected_model != "deepseek-chat":
                selected_model = "deepseek-chat"
                data = _post_once(selected_model)
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
                        # 从 market_data_dict 当前 symbol 的市场数据取 current_price
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
                    print("[WARN] 模型输出未包含 trade_signal_args，已按扁平 JSON 自动兼容包裹。")
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
                print("[WARN] 模型输出无法解析为有效 JSON，使用安全兜底：hold。")

        # 统一规范化与约束检查：确保信号与手数可执行、键完整
        if isinstance(args, dict):
            try:
                state = (market_data_dict.get(symbol) or {}).get('llm_state') or {}
            except Exception:
                state = {}
            allowed_actions = state.get('allowed_actions', ['buy', 'hold'])
            lot_size = int(state.get('lot_size', 100) or 100)
            max_buyable_lots = int(state.get('max_buyable_lots', 0) or 0)
            max_sellable_lots = int(state.get('max_sellable_lots', 0) or 0)
            tplus1_sell_available = bool(state.get('tplus1_sell_available_today', False))
            # 进攻型基线与最小手数（可由上游在 llm_state 中配置）
            try:
                min_lot_count = int(state.get('min_lot_count', 1) or 1)
            except Exception:
                min_lot_count = 1
            try:
                default_position_fraction = float(state.get('default_position_fraction', 0.25) or 0.25)
            except Exception:
                default_position_fraction = 0.25

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
            if sig == 'buy':
                # 冷却期禁止买入
                try:
                    md_local = (market_data_dict.get(symbol) or {})
                    if bool(md_local.get('buy_cooldown', False)):
                        sig = 'hold'
                        qty_lots = 0
                except Exception:
                    pass
                # 策略门槛硬性校验：仅当至少一个 BUY 触发成立时允许买入
                try:
                    md_local = (market_data_dict.get(symbol) or {})
                    flags = compute_strategy_flags(md_local)
                except Exception:
                    flags = {}
                is_trend_buy_strict = bool(flags.get('is_trend_buy_strict'))
                is_exploratory_buy = bool(flags.get('is_exploratory_buy'))
                is_mean_reversion_buy = bool(flags.get('is_mean_reversion_buy'))
                if not (is_trend_buy_strict or is_exploratory_buy or is_mean_reversion_buy):
                    sig = 'hold'
                    qty_lots = 0

                # 提升至激进基线（不低于 min_lot_count）
                try:
                    baseline_lots = max(min_lot_count, int(math.floor(max_buyable_lots * default_position_fraction)))
                except Exception:
                    baseline_lots = min_lot_count
                if max_buyable_lots > 0 and qty_lots < baseline_lots:
                    qty_lots = min(max_buyable_lots, baseline_lots)

                # 探索BUY限制：若仅为探索BUY，强制手数≤min_lot_count
                try:
                    if (not is_trend_buy_strict) and is_exploratory_buy:
                        qty_lots = min(qty_lots, min_lot_count)
                except Exception:
                    pass

                # 防追高：上轨扩张、EMA20偏离、当日大涨
                try:
                    md_local = (market_data_dict.get(symbol) or {})
                    current_price = md_local.get('current_price')
                    intraday_local = md_local.get('intraday') or {}
                    ema20_val = intraday_local.get('factor_ema_20') or intraday_local.get('ema20') or md_local.get('ema20')
                    boll_upper_val = intraday_local.get('factor_boll_upper')
                    today_change_pct = md_local.get('today_change_pct', 0.0)
                    state_local = md_local.get('llm_state') or {}
                    has_position_local = bool(state_local.get('has_position', False))
                    price_f = float(current_price) if current_price is not None else None
                    ema20_f = float(ema20_val) if ema20_val is not None else None
                    boll_upper_f = float(boll_upper_val) if boll_upper_val is not None else None
                    ratio = (price_f / ema20_f) if (price_f is not None and ema20_f and ema20_f > 0) else None
                    is_expansion = False
                    if boll_upper_f is not None and price_f is not None and price_f >= boll_upper_f:
                        is_expansion = True
                    if ratio is not None and ratio >= 1.01:
                        is_expansion = True
                    try:
                        day_pct_f = float(today_change_pct or 0.0)
                        if day_pct_f >= 0.03:
                            is_expansion = True
                    except Exception:
                        pass
                    if is_expansion:
                        qty_lots = min(qty_lots, min_lot_count)
                    if has_position_local and (ratio is not None) and (ratio > 1.01):
                        qty_lots = min(qty_lots, min_lot_count)
                except Exception:
                    pass

                # 下跌阶段上限：总持仓≤3手（当前持仓= max_sellable_lots），买入不得超限
                try:
                    flags_down = bool(flags.get('is_in_downtrend_cap'))
                except Exception:
                    flags_down = False
                if flags_down:
                    try:
                        current_hold_lots = int(max_sellable_lots)
                    except Exception:
                        current_hold_lots = 0
                    cap_remaining = max(0, 3 - current_hold_lots)
                    if qty_lots > cap_remaining:
                        qty_lots = cap_remaining
                    if qty_lots <= 0:
                        sig = 'hold'
                        qty_lots = 0

                if max_buyable_lots >= 0 and qty_lots > max_buyable_lots:
                    qty_lots = max_buyable_lots

                if qty_lots < 1:
                    qty_lots = 0
                    sig = 'hold'
            elif sig in ('sell', 'close'):
                if not tplus1_sell_available:
                    sig = 'hold'
                    qty_lots = 0
                else:
                    if sig == 'close':
                        # close：用全部可卖手数表达
                        qty_lots = max_sellable_lots
                    else:
                        # sell：部分减仓
                        if qty_lots < 1:
                            sig = 'hold'
                            qty_lots = 0
                        elif max_sellable_lots >= 0 and qty_lots > max_sellable_lots:
                            qty_lots = max_sellable_lots
                        try:
                            md_local = (market_data_dict.get(symbol) or {})
                            flags = compute_strategy_flags(md_local)
                            overbought_flag = bool(flags.get('is_overbought_sell'))
                            rsi6_val = md_local.get('factor_rsi_6')
                            if overbought_flag and (rsi6_val is not None):
                                rsi6_f = float(rsi6_val)
                                if rsi6_f >= 80.0 and ('close' in allowed_actions):
                                    sig = 'close'
                                    qty_lots = max_sellable_lots
                                elif rsi6_f >= 75.0:
                                    target = int(math.floor(max_sellable_lots * 0.5))
                                    qty_lots = max(qty_lots, target)
                                elif rsi6_f >= 70.0:
                                    target = int(math.floor(max_sellable_lots * 0.3))
                                    qty_lots = max(qty_lots, target)
                        except Exception:
                            pass
            else:
                # hold
                qty_lots = 0

            entry_price = args.get('entry_price')
            if entry_price is None:
                # 兜底使用当前价
                try:
                    entry_price = (market_data_dict.get(symbol) or {}).get('current_price')
                except Exception:
                    entry_price = None

            # 失效条件兜底：优先 stop_loss，其次 EMA20 连续两日下破建议
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

            # 风险估算（以股数计）：风险金额≈|entry-stop|*qty_lots*lot_size
            risk_usd = args.get('risk_usd')
            try:
                if risk_usd is None and (stop_loss is not None) and (entry_price is not None):
                    risk_usd = abs(float(entry_price) - float(stop_loss)) * int(qty_lots) * int(lot_size)
            except Exception:
                pass

            # 输出字段规范化与精简
            allowed_keys = {
                'symbol', 'signal', 'quantity', 'entry_price', 'leverage', 'confidence',
                'invalidation_condition', 'profit_target', 'stop_loss', 'risk_usd',
                'stop_loss_pct', 'tp_trailing_pct'
            }

            # HOLD：强制精简为可机读的最小集合
            if sig == 'hold':
                qty_lots = 0
                args['confidence'] = 0.0
                for k in ['profit_target', 'stop_loss', 'invalidation_condition', 'stop_loss_pct', 'tp_trailing_pct']:
                    if k in args:
                        args.pop(k, None)

            # BUY：若缺失风控百分比，填充安全默认值
            if sig == 'buy':
                if args.get('stop_loss_pct') is None:
                    args['stop_loss_pct'] = 0.05
                if args.get('tp_trailing_pct') is None:
                    args['tp_trailing_pct'] = 0.03

            normalized = {
                'symbol': args.get('symbol') or symbol,
                'signal': sig,
                'quantity': int(qty_lots),
                'entry_price': entry_price,
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

