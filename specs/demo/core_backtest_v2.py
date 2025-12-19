import os
import tinyshare as ts
import json
import pandas as pd
from typing import Dict, Any
from dotenv import load_dotenv

# Import portfolio management
from simple_portfolio import SimplePortfolio

# Import the V3 Engine
from strategy_engine import StrategyEvaluator

load_dotenv()

def normalize_symbol(sym: str):
    s = str(sym or '').strip().upper()
    if not s: return '', 'SZ'
    if '.' in s:
        base, exch = s.split('.', 1)
        return base.strip().zfill(6), exch.strip().upper()
    base = s.zfill(6)
    exch = 'SH' if base.startswith(('6', '5')) else 'SZ'
    return base, exch

def execute_backtest_v2(
    run_id: str,
    symbol: str,
    start_date: str,
    end_date: str,
    strategy_config: Dict[str, Any],
    user_id: str = None
):
    print(f"🚀 Starting V3 Backtest (Dynamic Engine) for {symbol}...")

    # 1. Initialize Evaluator (Brain)
    try:
        evaluator = StrategyEvaluator(strategy_config)
        print("✅ StrategyEvaluator V3 initialized.")
    except Exception as e:
        print(f"❌ Invalid Strategy Config: {e}")
        return {'error': str(e)}

    # 2. Fetch Data
    token = os.getenv("TINYSHARE_TOKEN")
    ts.set_token(token)
    pro = ts.pro_api()
    
    norm_symbol, exch = normalize_symbol(symbol)
    ts_code = f"{norm_symbol}.{exch}"
    
    df = pd.DataFrame()
    try:
        # Fetch history with buffer for MA/EMA calculation
        s_dt = pd.to_datetime(start_date) - pd.Timedelta(days=365) # 1 year buffer for slow EMAs
        
        # Try stocks
        df = pro.stk_factor(ts_code=ts_code, start_date=s_dt.strftime('%Y%m%d'), end_date=pd.to_datetime(end_date).strftime('%Y%m%d'))
        
        # Try ETFs if empty
        if df is None or df.empty:
             df = pro.fund_daily(ts_code=ts_code, start_date=s_dt.strftime('%Y%m%d'), end_date=pd.to_datetime(end_date).strftime('%Y%m%d'))
    except Exception as e:
        print(f"Data fetch error: {e}")
        return {'error': 'data_fetch_error'}
    
    if df is None or df.empty:
        return {'error': 'no_data'}

    # Standardize Columns
    if 'trade_date' in df.columns: df = df.rename(columns={'trade_date': 'date'})
    df['date'] = pd.to_datetime(df['date'].astype(str))
    df = df.sort_values('date').reset_index(drop=True)
    df['close'] = pd.to_numeric(df['close'])
    # Ensure 'vol' exists
    if 'vol' not in df.columns and 'volume' in df.columns: df['vol'] = df['volume']
    
    # Ensure High/Low exists for Slippage/Limit checks
    if 'high' not in df.columns: df['high'] = df['close']
    if 'low' not in df.columns: df['low'] = df['close']

    # 3. V3 Magic: Dynamic Data Preparation
    try:
        df = evaluator.prepare_data(df)
    except Exception as e:
        print(f"❌ Indicator Calculation Error: {e}")
        return {'error': f"Indicator Error: {str(e)}"}

    # 4. Filter for Backtest Range
    df_main = df[(df['date'] >= pd.to_datetime(start_date)) & (df['date'] <= pd.to_datetime(end_date))].copy()
    
    if df_main.empty:
        return {'error': 'no_data_in_range'}

    # 5. Portfolio Setup (A-Share Mode)
    initial_cash = 100000.0
    # Use default A-share rates: 0.025% commission, 0.05% stamp duty (sell only)
    portfolio = SimplePortfolio(initial_cash=initial_cash, commission_rate=0.00025, stamp_duty_rate=0.0005)
    lot_size = 100
    
    # 6. Event Loop
    records = df_main.to_dict('records')
    trade_history = []
    equity_curve = []
    
    for row in records:
        dstr = row['date'].strftime('%Y-%m-%d')
        price = row['close']
        high = row.get('high', price)
        low = row.get('low', price)
        
        # Mark to Market
        portfolio.update_price(norm_symbol, price)

        # Position Info
        pos_info = None
        if norm_symbol in portfolio.positions and portfolio.positions[norm_symbol].quantity > 0:
            pos = portfolio.positions[norm_symbol]
            pos_info = {
                'quantity': pos.quantity,
                'entry_price': pos.entry_price,
                'highest_price': getattr(pos, 'highest_price', pos.entry_price),
                'buy_date': getattr(pos, 'buy_date', None)
            }

        # Call Brain
        decision = evaluator.evaluate(row, pos_info)
        signal = decision.get('signal', 'hold')
        reason = decision.get('reason', '')
        
        qty = 0
        
        if signal == 'buy':
            # Sizing
            sizing_rule = strategy_config.get('position_sizing', {})
            target_pct = float(sizing_rule.get('value', 25)) / 100.0 if sizing_rule.get('method') == 'percent_of_equity' else 0.25
            
            amt_to_buy = portfolio.total_asset * target_pct
            # Calculate max quantity considering estimated cost with fees (1.001 buffer)
            est_cost_per_share = price * (1 + portfolio.commission_rate)
            est_qty = int(amt_to_buy // (est_cost_per_share * lot_size)) * lot_size
            
            # Check available cash hard limit
            max_qty_cash = int(portfolio.available_cash // (est_cost_per_share * lot_size)) * lot_size
            qty = min(est_qty, max_qty_cash)
            
            if qty > 0:
                # SLIPPAGE: Buy at slightly higher price (0.1%), capped at daily high
                exec_price = min(price * 1.001, high)
                
                success = portfolio.execute_decision(
                    symbol=norm_symbol, 
                    quantity=qty, 
                    price=exec_price, 
                    signal='buy',
                    current_date=dstr
                )
                if success:
                    print(f"[{dstr}] BUY {qty} @ {exec_price:.2f} | {reason}")

        elif signal == 'sell':
            if pos_info:
                qty = pos_info['quantity']
                entry_p = pos_info['entry_price']
                
                # SLIPPAGE: Sell at slightly lower price (0.1%), floored at daily low
                exec_price = max(price * 0.999, low)
                
                success = portfolio.execute_decision(
                    symbol=norm_symbol, 
                    quantity=qty, 
                    price=exec_price, 
                    signal='close', # Use 'close' to sell all allocated qty
                    current_date=dstr
                )
                
                if success:
                    pnl = (exec_price - entry_p) * qty # Approximate Gross PnL
                    # Note: Net PnL would be lower due to fees calculated inside portfolio
                    
                    print(f"[{dstr}] SELL {qty} @ {exec_price:.2f} | {reason} | Gross PnL: {pnl:.2f}")
                    
                    # Record for Diagnosis
                    cost = entry_p * qty
                    pnl_pct = pnl / cost if cost > 0 else 0
                    
                    ctx = {'price': price}
                    for k in ['rsi_6', 'rsi_12', 'ema_20', 'macd', 'sma_200']:
                        if k in row: ctx[k] = row[k]
                    
                    trade_history.append({
                        'date': dstr,
                        'reason': reason,
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'context': ctx
                    })
                else:
                    # Failed (likely T+1 locked)
                    pass
                    # print(f"[{dstr}] SELL REJECTED (T+1 or other)")
        
        # Record daily equity
        equity_curve.append({
            'date': dstr,
            'equity': float(portfolio.total_asset),
            'cash': float(portfolio.available_cash)
        })

    print("✅ Backtest Completed.")
    
    wins = [t for t in trade_history if t['pnl'] > 0]
    win_rate = len(wins) / len(trade_history) if trade_history else 0.0
    
    losses = [t for t in trade_history if t['pnl'] <= 0]
    losses.sort(key=lambda x: x['pnl'])
    bad_trades = losses[:3]
    
    report = {
        'win_rate': win_rate,
        'total_trades': len(trade_history),
        'bad_trades': bad_trades
    }
    
    return {
        'status': 'success', 
        'final_equity': portfolio.total_asset,
        'report': report,
        'equity_curve': equity_curve
    }
