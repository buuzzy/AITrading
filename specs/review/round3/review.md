这是基于我们对张江高科（以及航天发展）回测的深度复盘后，得出的最终优化指令。
这套修改旨在将策略从“过度防御”转变为“攻守兼备”，重点解决拿不住主升浪和不敢抄底回调的问题。
请按以下步骤修改代码。
第一部分：修改 trade_decision_simple_AI.py
此文件改动最大，涉及提示词工程（Prompt Engineering）和 Python 硬规则（Guardrails）的双重松绑。
1. 修改 SYSTEM_PROMPT_TEXT
目标：在系统层面确立“超级趋势”的最高地位。
code
Python
# 请替换原有的 SYSTEM_PROMPT_TEXT
SYSTEM_PROMPT_TEXT = (
    "You are a Contrarian A-share Trading Agent. You profit from market overreaction.\n"
    "Your strategy is: Buy when others are fearful, Sell when others are greedy.\n"
    "\n"
    "*** CRITICAL: HOW TO USE EXTERNAL TA (THE 'SENTIMENT INDICATOR') ***\n"
    "The provided 'EXTERNAL TECHNICAL ANALYSIS' represents the 'Naive Crowd Sentiment'.\n"
    "You must use it as a CONTRARIAN INDICATOR in extreme zones, BUT respect the TREND:\n"
    "\n"
    "1. THE 'SUPER TREND' EXCEPTION (HIGHEST PRIORITY):\n"
    "   - IF `is_super_trend` is True:\n"
    "   - ACTION: DO NOT SELL even if RSI is high (unless RSI > 90). IGNORE Bearish TA unless price breaks EMA10.\n"
    "   - INTENT: Ride the bubble. The crowd is greedy, but the trend is too strong to short.\n"
    "\n"
    "2. THE 'BULL TRAP' SCENARIO (Normal Uptrend -> SELL):\n"
    "   - IF `is_super_trend` is False AND External TA says 'Bullish'...\n"
    "   - AND Quant flags show `is_extreme_overbought` OR RSI(6) > 80:\n"
    "   - ACTION: SELL or CLOSE positions.\n"
    "\n"
    "3. THE 'BEAR TRAP' SCENARIO (TA says Bearish -> YOU BUY):\n"
    "   - IF External TA says 'Downtrend', 'Bearish'...\n"
    "   - AND Quant flags show `is_momentum_buy` OR price is near support (EMA20/Bollinger Lower) OR RSI < 30:\n"
    "   - ACTION: BUY aggressively.\n"
    "\n"
    "*** IMPORTANT: TIMING & EXECUTION ***\n"
    "You are analyzing market data AFTER the market close (Day T).\n"
    "Your 'Buy' signal will be executed at the OPEN PRICE of the NEXT TRADING DAY (Day T+1).\n"
    "\n"
    "*** EXECUTION RULES ***\n"
    "- Buying:\n"
    "  - If 'Bear Trap' or 'Cooldown Release' detected: BUY.\n"
    "  - **Pyramiding**: If holding position with profit > 5% AND `is_momentum_buy` is True: ADD position (Aggressive).\n"
    "- Selling:\n"
    "  - If 'Bull Trap' detected (and NOT Super Trend): SELL.\n"
    "  - If Trend Breaks (Close < EMA20): SELL.\n"
    "\n"
    "Output strictly in JSON format with 'trade_signal_args'."
)
2. 修改 compute_strategy_flags 函数
目标：增加“冷却释放”和“利润加仓”的辅助标志。
code
Python
# 在 compute_strategy_flags 函数内部，return 之前，增加以下计算逻辑：
    
    # ... (原有代码保持不变)

    # [新增] 7. 动态冷却释放标志 (Dynamic Cooldown Release)
    # 如果 RSI 快速掉到 40 以下，或者价格回踩 EMA20 附近 (1.5%以内) 且未跌破
    is_cooldown_release_met = False
    try:
        if (rsi6 is not None and rsi6 < 40.0):
            is_cooldown_release_met = True
        if (price is not None and ema20 is not None):
            # 回踩 EMA20 上方附近 (1.00 ~ 1.015)
            if (price >= ema20) and (price <= ema20 * 1.015):
                is_cooldown_release_met = True
    except Exception:
        pass

    # ... (原有代码)

    return {
        # ... (保留原有字段)
        'is_cooldown_release_met': bool(is_cooldown_release_met), # [新增]
    }
3. 修改 build_market_prompt 函数中的 corrections_block
目标：用自然语言告诉 LLM 新的战术规则。
code
Python
# 替换原有的 corrections_block
    corrections_block = (
        "策略修正摘要（需严格遵守）：\n"
        "- 超级趋势豁免 (Super Trend)：若 `is_super_trend`=True，禁止任何止盈/减仓，除非 RSI(6) > 90 或收盘价跌破 EMA10。允许在趋势中无视超买。\n"
        "- 浮盈加仓 (Pyramiding)：若当前持仓浮盈 > 5% 且 `is_momentum_buy`=True，允许加仓至 40%-50% 总仓位。\n"
        "- 冷却解除 (Cooldown Release)：若 `is_in_buy_cooldown`=True 但 `is_cooldown_release_met`=True (回踩EMA20或超卖)，允许立即买入，无视冷却。\n"
        "- 左侧抄底：熊市陷阱/超卖区域买入时，基础仓位 1-5 手（试错）。\n"
        "- 下跌风控：若价格 < EMA20 且跌幅 > 3%（有效破位），强制减仓/清仓；若仅在 EMA20 附近震荡，允许持有。\n"
    )
4. 修改 trade_decision_provider 函数中的 Python 硬规则
目标：给 Python 侧的拦截逻辑松绑。
code
Python
# ... (定位到 if sig == 'buy': 附近)
            if sig == 'buy':
                # [修改] 冷却期检查：增加豁免条件
                try:
                    md_local = (market_data_dict.get(symbol) or {})
                    flags_local = compute_strategy_flags(md_local) # 确保获取最新 flags
                    in_cooldown = bool(md_local.get('buy_cooldown', False))
                    release_met = bool(flags_local.get('is_cooldown_release_met', False))
                    
                    # 如果在冷却期，且不满足释放条件，则拦截
                    if in_cooldown and not release_met:
                        sig = 'hold'
                        qty_lots = 0
                except Exception:
                    pass

                # [修改] 策略门槛硬性校验：增加对“冷却释放”的支持
                # ... (获取 flags)
                is_super_trend = bool(flags.get('is_super_trend'))
                # ...
                is_cooldown_release_met = bool(flags.get('is_cooldown_release_met')) # 新增

                # 允许买入的条件集扩大
                if not (is_trend_buy_strict or is_exploratory_buy or is_mean_reversion_buy or is_momentum_buy or is_super_trend or is_cooldown_release_met):
                    sig = 'hold'
                    qty_lots = 0
                
                # [新增] 浮盈加仓逻辑 (Pyramiding)
                # 如果是加仓，且有浮盈，放宽手数限制
                try:
                    state = md_local.get('llm_state') or {}
                    avg_price = state.get('avg_entry_price')
                    curr_price = state.get('current_price')
                    if avg_price and curr_price and avg_price > 0:
                        profit_pct = (curr_price - avg_price) / avg_price
                        if profit_pct > 0.05 and is_momentum_buy:
                            # 允许买更多，例如提升到 50% 仓位
                            target_lots = int(max_buyable_lots * 0.5)
                            qty_lots = max(qty_lots, target_lots)
                except Exception:
                    pass

            # ... (定位到 elif sig in ('sell', 'close'): 附近)
            elif sig in ('sell', 'close'):
                # ...
                try:
                    # [修改] 超买卖出：给 Super Trend 发免死金牌
                    is_super_trend = bool(flags.get('is_super_trend')) # 获取标志
                    rsi6_val = md_local.get('factor_rsi_6')
                    
                    if is_super_trend:
                        # 超级趋势中，只有极度极度超买才卖
                        if rsi6_val is not None and float(rsi6_val) > 90.0:
                             # 允许卖出，逻辑不变
                             pass
                        else:
                             # 强行取消卖出，继续持有
                             sig = 'hold'
                             qty_lots = 0
                    else:
                        # 非超级趋势，按原逻辑（RSI>80平仓，>75减仓）
                        # ... (原有逻辑)
                        pass
                except Exception:
                    pass
第二部分：修改 backtest.py (配合动态冷却)
虽然我们在 trade_decision_simple_AI.py 里做了豁免，但为了保持逻辑一致性，建议在 backtest.py 里也做一个小的状态更新，确保 buy_cooldown 的状态能被正确重置。
修改主循环中的冷却状态更新
定位：在 backtest.py 的 for dstr in process_days: 循环内部，计算 md_one 之后，trade_decision_provider 调用之前。
code
Python
# ... (md_one 计算完毕)
        
        # [新增] 动态冷却重置逻辑 (Dynamic Cooldown Reset)
        # 如果当前价格满足回踩或超卖，提前结束冷却期
        if buy_cooldown_until and dstr < buy_cooldown_until:
            try:
                # 简单的本地判断
                curr_rsi6 = md_one.get('factor_rsi_6')
                curr_p = md_one.get('current_price')
                curr_ema = md_one.get('current_close_20_ema')
                
                reset_cooldown = False
                # 条件1: RSI 超卖
                if curr_rsi6 is not None and curr_rsi6 < 40.0:
                    reset_cooldown = True
                # 条件2: 回踩 EMA20 附近 (1%以内) 且未跌破
                elif curr_p and curr_ema and curr_p >= curr_ema and (curr_p <= curr_ema * 1.015):
                    reset_cooldown = True
                
                if reset_cooldown:
                    buy_cooldown_until = None # 立即解除
                    # 同时更新 md_one 里的状态，供本次决策使用
                    md_one['buy_cooldown'] = False
            except Exception:
                pass
        
        # ... (后续代码保持不变)
🏁 总结：这将带来什么改变？
不再卖飞：只要 is_super_trend 亮起，无论 RSI 涨到 80 还是 85，策略都会死死拿住筹码，直到 RSI 冲破 90 或趋势逆转。这能让你吃完茅台 9 月份的主升浪。
敢于回补：如果你在高位止盈了，一旦股价回踩 EMA20 企稳，策略会立即解除冷却期，允许你杀个回马枪（倒车接人）。
浮盈加仓：如果第一笔试探仓位赚了 5%，策略会变得更有底气，开始上仓位，而不是一直用 1 手玩到底。