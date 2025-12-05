import os
import shutil
import tinyshare as ts
import sys
import json
import math
import logging
from typing import Dict, Any, List, Optional
import time
import uuid
import requests

import pandas as pd
import numpy as np
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import portfolio management
from simple_portfolio import SimplePortfolio

# Import AI decision logic
from trade_decision_simple_AI import (
    trade_decision_provider as ai_trade_decision_provider,
    market_data_to_string_for_symbol,
    portfolio_to_string,
    SYSTEM_PROMPT_TEXT,
    build_market_prompt,
    compute_strategy_flags,
)

# --- Dify Technical Analysis Integration ---
try:
    from py_trader.live_trader import request_technical_analysis as request_technical_analysis_dify
except Exception:
    try:
        from livetrade import request_technical_analysis as request_technical_analysis_dify
    except Exception:
        def request_technical_analysis_dify(symbol: str, ts_code: str, today: str, prev_open: str):
            return None

# --- Helper Functions ---

def normalize_symbol(sym: str):
    """Normalize A-share code and infer exchange."""
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
    # ETF prefixes
    elif base.startswith(('510', '512', '513', '515', '518')):
        exch = 'SH'
    elif base.startswith(('159', '150')):
        exch = 'SZ'
    else:
        exch = 'SH' if base[0] == '6' else 'SZ'
    return base, exch

def compute_ema(series: pd.Series, span: int = 20) -> pd.Series:
    try:
        return series.ewm(span=span, adjust=False).mean()
    except Exception:
        return pd.Series([None] * len(series))

def compute_macd_full(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
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

def compute_bollinger(series: pd.Series, period: int = 20, k: float = 2.0):
    try:
        ma = series.rolling(window=period, min_periods=1).mean()
        std = series.rolling(window=period, min_periods=1).std()
        upper = ma + k * std
        lower = ma - k * std
        return ma, upper, lower
    except Exception:
        n = len(series)
        none_series = pd.Series([None] * n)
        return none_series, none_series, none_series

def compute_kdj(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 9):
    try:
        ll = low.rolling(window=n, min_periods=1).min()
        hh = high.rolling(window=n, min_periods=1).max()
        denom = (hh - ll).replace(0, np.nan)
        rsv = ((close - ll) / denom) * 100.0
        k = rsv.ewm(alpha=1/3, adjust=False).mean()
        d = k.ewm(alpha=1/3, adjust=False).mean()
        j = 3.0 * k - 2.0 * d
        return k, d, j
    except Exception:
        nlen = len(close)
        none_series = pd.Series([None] * nlen)
        return none_series, none_series, none_series

def compute_cci(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 20):
    try:
        tp = (high + low + close) / 3.0
        ma = tp.rolling(window=n, min_periods=1).mean()
        md = (tp - ma).abs().rolling(window=n, min_periods=1).mean()
        denom = (0.015 * md).replace(0, np.nan)
        cci = (tp - ma) / denom
        return cci
    except Exception:
        return pd.Series([None] * len(close))

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
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

        rsi.loc[(avg_loss == 0) & (avg_gain > 0)] = 100.0
        rsi.loc[(avg_gain == 0) & (avg_loss > 0)] = 0.0
        rsi.loc[(avg_gain == 0) & (avg_loss == 0)] = 50.0

        return rsi
    except Exception:
        return pd.Series([np.nan] * len(series))

def build_market_data_for_day(symbol: str, window_df: pd.DataFrame) -> Dict[str, Any]:
    closes = window_df['close']
    vols = window_df['vol'] if 'vol' in window_df.columns else pd.Series()
    
    # EMA on the window
    ema10 = compute_ema(closes, 10)
    ema20 = compute_ema(closes, 20)
    ema60 = compute_ema(closes, 60)
    
    # SMAs
    ma5 = closes.rolling(window=5).mean()
    ma10 = closes.rolling(window=10).mean()
    ma20 = closes.rolling(window=20).mean()
    ma60 = closes.rolling(window=60).mean()

    # MACD for slope calculation
    try:
        _, _, hist = compute_macd_full(closes)
        macd_hist_last = float(hist.iloc[-1]) if not pd.isna(hist.iloc[-1]) else 0.0
        macd_hist_prev = float(hist.iloc[-2]) if len(hist) > 1 and not pd.isna(hist.iloc[-2]) else 0.0
        macd_slope = macd_hist_last - macd_hist_prev
    except Exception:
        macd_slope = 0.0

    # Bollinger for Breakout detection
    try:
        _, upper, _ = compute_bollinger(closes)
        boll_upper = float(upper.iloc[-1]) if not pd.isna(upper.iloc[-1]) else None
    except Exception:
        boll_upper = None

    def _last(series):
        if series.empty or pd.isna(series.iloc[-1]): return None
        return float(series.iloc[-1])

    return {
        'frequency': '1d',
        'current_price': float(closes.iloc[-1]),
        'current_ema10': _last(ema10),
        'current_close_20_ema': _last(ema20),
        'current_ema60': _last(ema60),
        'current_boll_upper': boll_upper,
        'macd_hist_slope': macd_slope,
        'current_ma5': _last(ma5),
        'current_ma10': _last(ma10),
        'current_ma20': _last(ma20),
        'current_ma60': _last(ma60),
        'mid_prices': [float(x) for x in closes.tolist()],
        'recent_vol': [float(x) for x in vols.tolist()],
        'ema_20_array': [None if (x is None or (isinstance(x, float) and math.isnan(x))) else float(x) for x in ema20.tolist()],
    }

# --- Data Fetching ---

def _fetch_daily_weekly_from_api(pro, ts_code: str, prev_open: str, daily_len: int = 80, weekly_len: int = 40):
    d_end = prev_open
    try:
        d_start = (pd.to_datetime(prev_open) - pd.Timedelta(days=365)).strftime('%Y%m%d')
    except Exception:
        d_start = prev_open
    
    daily_df = None
    try:
        daily_df = pro.fund_daily(ts_code=ts_code, start_date=d_start, end_date=d_end)
    except Exception:
        daily_df = None
    
    weekly_df = None
    try:
        weekly_df = pro.weekly(ts_code=ts_code, start_date=d_start, end_date=d_end)
    except Exception:
        weekly_df = None
        
    if daily_df is None or daily_df.empty:
        try:
            daily_df = pro.daily(ts_code=ts_code, start_date=d_start, end_date=d_end)
        except Exception:
            daily_df = None
            
    daily = []
    try:
        if daily_df is not None and not daily_df.empty:
            daily_df = daily_df.rename(columns={'trade_date': 'date'})
            daily_df['date'] = pd.to_datetime(daily_df['date'].astype(str))
            daily_df = daily_df.sort_values('date')
            daily_df = daily_df[daily_df['date'] <= pd.to_datetime(prev_open)]
            daily_df = daily_df.tail(daily_len)
            for _, r in daily_df.iterrows():
                daily.append({
                    'date': r['date'].strftime('%Y%m%d'),
                    'open': float(r['open']),
                    'high': float(r['high']),
                    'low': float(r['low']),
                    'close': float(r['close'])
                })
    except Exception:
        daily = []
        
    weekly = []
    try:
        if weekly_df is not None and not weekly_df.empty:
            weekly_df = weekly_df.rename(columns={'trade_date': 'date'})
            weekly_df['date'] = pd.to_datetime(weekly_df['date'].astype(str))
            weekly_df = weekly_df.sort_values('date')
            weekly_df = weekly_df[weekly_df['date'] <= pd.to_datetime(prev_open)]
            weekly_df = weekly_df.tail(weekly_len)
            for _, r in weekly_df.iterrows():
                weekly.append({
                    'date': r['date'].strftime('%Y%m%d'),
                    'open': float(r['open']),
                    'high': float(r['high']),
                    'low': float(r['low']),
                    'close': float(r['close'])
                })
        elif daily_df is not None and not daily_df.empty:
            tmp = daily_df.rename(columns={'trade_date': 'date'}).copy()
            tmp['date'] = pd.to_datetime(tmp['date'].astype(str))
            tmp = tmp[tmp['date'] <= pd.to_datetime(prev_open)]
            tmp['week'] = tmp['date'].dt.to_period('W-FRI')
            w_agg = tmp.groupby('week').agg({'open':'first','high':'max','low':'min','close':'last','date':'last'}).reset_index(drop=True)
            w_agg = w_agg.tail(weekly_len)
            for _, r in w_agg.iterrows():
                weekly.append({
                    'date': r['date'].strftime('%Y%m%d'),
                    'open': float(r['open']),
                    'high': float(r['high']),
                    'low': float(r['low']),
                    'close': float(r['close'])
                })
    except Exception:
        weekly = []
    return daily, weekly

# --- Dify API ---

def _request_technical_analysis_dify_v2(stock_code: str, daily: list, weekly: list, print_full: bool = False, excerpt_len: int = 120):
    api_key = os.getenv('DIFY_API_KEY')
    url = os.getenv('DIFY_API_URL') or 'https://api.dify.ai/v1/workflows/run'
    if not api_key:
        return None
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    payload = {
        'inputs': {
            'stock_code': stock_code,
            'daily': json.dumps(daily, ensure_ascii=False),
            'weekly': json.dumps(weekly, ensure_ascii=False)
        },
        'response_mode': 'blocking',
        'user': 'backtest'
    }
    try:
        # print(f"[DIFY] POST {url} ...")
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=180)
        if r.status_code == 200:
            try:
                obj = r.json()
                data = obj.get('data') or {}
                outputs = data.get('outputs') or {}
                text = None
                if isinstance(outputs, dict):
                    preferred_keys = ['technical_analysis', 'text', 'result']
                    for k in preferred_keys:
                        if k in outputs and isinstance(outputs.get(k), str) and outputs.get(k).strip():
                            text = outputs.get(k)
                            break
                    if not text:
                        for v in outputs.values():
                            if isinstance(v, str) and v.strip():
                                text = v
                                break
                elif isinstance(outputs, str):
                    text = outputs
                return text
            except Exception:
                return None
        return None
    except Exception:
        return None

def _request_technical_analysis_dify_streaming(stock_code: str, daily: list, weekly: list, print_full: bool = False, excerpt_len: int = 120):
    # Simplified streaming implementation for core module
    return _request_technical_analysis_dify_v2(stock_code, daily, weekly, print_full, excerpt_len)

# --- Supabase Helpers ---

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
        return False, r.text
    except Exception as e:
        return False, str(e)

def _supabase_upsert_trade(run_id: str, symbol: str, date_str: str, row: Dict[str, Any]):
    base_sym, _ = normalize_symbol(symbol)
    sig = str(row.get('signal') or '').lower()
    side = 'buy' if sig == 'buy' else ('sell' if sig in ('sell', 'close') else 'hold')
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
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

def _supabase_upsert_checkpoint(run_id: str, symbol: str, date_str: str, reason: str):
    base_sym, _ = normalize_symbol(symbol)
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'reason': str(reason),
    }
    return _supabase_upsert('checkpoints', [doc], on_conflict='run_id,symbol,date')

def _supabase_insert_error(run_id: str, symbol: str, date_str: str, source: str, code: str, message: str, raw: Dict[str, Any] = None):
    base_sym, _ = normalize_symbol(symbol)
    doc = {
        'run_id': run_id,
        'symbol': base_sym,
        'date': pd.to_datetime(date_str, format=('%Y-%m-%d' if '-' in date_str else '%Y%m%d')).strftime('%Y-%m-%d'),
        'source': str(source or 'other'),
        'code': str(code or 'unknown'),
        'message': str(message or ''),
        'raw': raw if isinstance(raw, dict) else None,
    }
    return _supabase_upsert('error', [doc]) # Table name 'error' per docs

def _supabase_update_run_status(run_id: str, status: str):
    payload = [{
        'run_id': run_id,
        'status': status,
        'finished_at': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S') if status == 'completed' else None,
    }]
    return _supabase_upsert('runs', payload, on_conflict='run_id')

# --- Cloudflare R2 Helpers ---

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

def _r2_upload_data(data_str: str, key_prefix: str, run_id: str, symbol: str, date_str: str, ext: str = 'json'):
    client_bucket, err = _r2_client()
    if not client_bucket:
        return False, err
    s3, bucket = client_bucket
    
    # Updated path structure: runs/{run_id}/{filename}
    # This ensures isolation by run_id, avoiding collisions between users/runs on same day/stock
    
    filename = f"llm_{symbol}.{ext}"
    if ext == 'csv':
        filename = f"trades_{symbol}.csv"
        
    key = f"aitrading/runs/{run_id}/{date_str}/{filename}"
    
    extra = {}
    if ext == 'json':
        extra['ContentType'] = 'application/json'
    elif ext == 'csv':
        extra['ContentType'] = 'text/csv'
        
    try:
        s3.put_object(Bucket=bucket, Key=key, Body=data_str.encode('utf-8'), **extra)
        return True, None
    except Exception as e:
        return False, str(e)

# --- State Restoration Helpers ---

def _fetch_run_trades(run_id: str):
    url, key = _supabase_creds()
    if not url or not key: return []
    endpoint = f"{url}/rest/v1/trades?run_id=eq.{run_id}&order=date.asc"
    try:
        r = requests.get(endpoint, headers=_supabase_headers(key, False), timeout=10)
        if r.status_code == 200:
            return r.json()
    except: pass
    return []

def _fetch_last_metric_date(run_id: str):
    url, key = _supabase_creds()
    if not url or not key: return None
    endpoint = f"{url}/rest/v1/daily_metrics?run_id=eq.{run_id}&order=date.desc&limit=1"
    try:
        r = requests.get(endpoint, headers=_supabase_headers(key, False), timeout=10)
        if r.status_code == 200:
            data = r.json()
            if data:
                return data[0]['date'] # YYYY-MM-DD
    except: pass
    return None

# --- Main Backtest Logic ---

def execute_backtest_job(
    run_id: str,
    symbol: str,
    start_date: str,
    end_date: str,
    strategy_config: Dict[str, Any] = None,
    user_id: str = None
):
    logger = logging.getLogger(f"job-{run_id}")
    # Force status update to ensure UI sees it
    _supabase_update_run_status(run_id, 'running')

    # Ensure inputs are strings
    start_date = str(start_date)
    end_date = str(end_date)

    norm_symbol, exch = normalize_symbol(symbol)
    symbol = norm_symbol
    ts_code = f"{symbol}.{exch}"
    is_shanghai = (exch == 'SH')
    
    if not strategy_config:
        strategy_config = {}
        
    model_name = strategy_config.get('model_name', 'deepseek-chat')
    initial_cash = float(strategy_config.get('initial_cash', 100000.0))
    lot_size = int(strategy_config.get('lot_size', 100))
    commission_rate = float(strategy_config.get('commission_rate', 0.0003))
    stamp_duty_rate = float(strategy_config.get('stamp_duty_rate', 0.0005))
    transfer_fee_rate = float(strategy_config.get('transfer_fee_rate', 0.00001))
    
    # 1. Fetch Data (TinyShare)
    token = os.getenv("TINYSHARE_TOKEN")
    if not token:
        _supabase_update_run_status(run_id, 'failed')
        return {'error': 'missing_tinyshare_token'}
        
    ts.set_token(token)
    pro = ts.pro_api()
    
    # Prefetch data logic (simplified from original)
    start_dt_safe = pd.to_datetime(start_date, errors='coerce')
    end_dt_safe = pd.to_datetime(end_date, errors='coerce')
    prefetch_start_dt = start_dt_safe - pd.Timedelta(days=90)
    prefetch_start_str = prefetch_start_dt.strftime('%Y%m%d')
    end_str = end_dt_safe.strftime('%Y%m%d')
    
    df = pd.DataFrame()
    is_etf = False
    
    # 1. Try Stock Factor (Stocks)
    try:
        df = pro.stk_factor(ts_code=ts_code, start_date=prefetch_start_str, end_date=end_str)
    except Exception:
        df = pd.DataFrame()

    # 2. If empty, Try Fund Daily (ETFs)
    if df is None or df.empty:
        try:
            df = pro.fund_daily(ts_code=ts_code, start_date=prefetch_start_str, end_date=end_str)
            if df is not None and not df.empty:
                is_etf = True
        except Exception:
            pass

    if df is not None and not df.empty:
        if 'trade_date' in df.columns:
            df = df.rename(columns={'trade_date': 'date'})
            
        date_str = df['date'].astype(str).str.replace('-', '', regex=False).str.strip()
        df['date'] = pd.to_datetime(date_str, format='%Y%m%d', errors='coerce')
        
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.to_datetime(end_date)
        
        # Filter date range
        df_all = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
        
        df = df_all[df_all['date'] <= end_dt].copy()
        df_main = df[(df['date'] >= start_dt) & (df['date'] <= end_dt)].copy()
        
        if df_main.empty:
            _supabase_update_run_status(run_id, 'failed')
            return {'error': 'no_data_in_range'}
            
        df_pre = df[df['date'] < start_dt].tail(30).copy()
        df = pd.concat([df_pre, df_main], ignore_index=True)
        df = df.sort_values('date').drop_duplicates(subset=['date']).reset_index(drop=True)
    else:
        _supabase_update_run_status(run_id, 'failed')
        return {'error': 'data_fetch_returned_empty'}

    if 'close' not in df.columns:
        _supabase_update_run_status(run_id, 'failed')
        return {'error': 'missing_close_price'}
        
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    closes = df['close']
    
    # --- Auto-calculate Indicators if missing (e.g. for ETFs) ---
    # Ensure we have basic indicators even if data source (fund_daily) didn't provide them
    try:
        if 'macd' not in df.columns or df['macd'].isnull().all():
            dif, dea, hist = compute_macd_full(closes)
            df['macd_dif'] = dif
            df['macd_dea'] = dea
            df['macd'] = hist
        
        if 'rsi_6' not in df.columns or df['rsi_6'].isnull().all():
            df['rsi_6'] = compute_rsi(closes, 6)
            df['rsi_12'] = compute_rsi(closes, 12)
            df['rsi_24'] = compute_rsi(closes, 24)
            
        if 'boll_upper' not in df.columns or df['boll_upper'].isnull().all():
            ma20, upper, lower = compute_bollinger(closes)
            df['boll_mid'] = ma20
            df['boll_upper'] = upper
            df['boll_lower'] = lower
            
        if 'kdj_k' not in df.columns or df['kdj_k'].isnull().all():
            highs = pd.to_numeric(df['high'], errors='coerce')
            lows = pd.to_numeric(df['low'], errors='coerce')
            k, d, j = compute_kdj(highs, lows, closes)
            df['kdj_k'] = k
            df['kdj_d'] = d
            df['kdj_j'] = j
            
        if 'cci' not in df.columns or df['cci'].isnull().all():
            highs = pd.to_numeric(df['high'], errors='coerce')
            lows = pd.to_numeric(df['low'], errors='coerce')
            df['cci'] = compute_cci(highs, lows, closes)
    except Exception as e:
        logger.warning(f"Indicator calculation failed: {e}")

    # Trading Calendar
    try:
        cal_df = pro.trade_cal(exchange=('SSE' if is_shanghai else 'SZSE'), start_date=start_date.replace('-',''), end_date=end_date.replace('-',''))
        if cal_df is not None and not cal_df.empty:
            open_days = sorted(cal_df.loc[cal_df['is_open'] == 1, 'cal_date'].astype(str).tolist())
        else:
            open_days = []
    except:
        open_days = sorted(df['date'].dt.strftime('%Y%m%d').tolist())

    # Ensure open_days are strictly within the requested range (filter out warm-up days from fallback)
    start_date_clean = start_date.replace('-', '')
    end_date_clean = end_date.replace('-', '')
    open_days = [str(d) for d in open_days if str(d) >= start_date_clean and str(d) <= end_date_clean]

    df['date_str'] = df['date'].dt.strftime('%Y%m%d')
    idx_map = {row['date_str']: i for i, row in df.iterrows()}
    
    # Initialize Portfolio
    portfolio = SimplePortfolio(initial_cash=initial_cash)
    
    # State
    actions = []
    can_sell_after = {}
    buy_cooldown_until = None

    # --- Resume Logic ---
    try:
        existing_trades = _fetch_run_trades(run_id)
        resumed_last_date = None
        
        if existing_trades:
            print(f"Resuming run {run_id} with {len(existing_trades)} existing trades...")
            # Sort by date
            existing_trades.sort(key=lambda x: x['date'])
            
            for t in existing_trades:
                t_date = t['date'].replace('-', '')
                t_signal = t['side']
                t_qty = float(t['qty']) if t['qty'] else 0
                t_price = float(t['price']) if t['price'] else 0
                
                if t_signal in ('buy', 'sell', 'close'):
                    portfolio.execute_decision(
                        symbol=symbol, 
                        quantity=t_qty, 
                        price=t_price, 
                        leverage=1.0, 
                        signal=t_signal
                    )
                    
                    actions.append({
                        'date': t_date,
                        'signal': t_signal,
                        'quantity': t_qty,
                        'price': t_price,
                        'success': True
                    })
                    
                    if t_signal == 'buy':
                        if t_date in open_days:
                            try:
                                idx = open_days.index(t_date)
                                if idx + 1 < len(open_days):
                                    can_sell_after[symbol] = open_days[idx + 1]
                            except: pass
                
                if not resumed_last_date or t_date > resumed_last_date:
                    resumed_last_date = t_date

        # Check daily metrics for last processed date (in case of hold days)
        last_metric_date = _fetch_last_metric_date(run_id)
        if last_metric_date:
            lmd = last_metric_date.replace('-', '')
            if not resumed_last_date or lmd > resumed_last_date:
                resumed_last_date = lmd
        
        if resumed_last_date:
            # Filter open_days to start AFTER resumed_last_date
            print(f"Skipping days up to {resumed_last_date}...")
            new_open_days = [d for d in open_days if d > resumed_last_date]
            if len(new_open_days) < len(open_days):
                # Update portfolio price to the close of resumed_last_date
                if resumed_last_date in idx_map:
                    i_resume = idx_map[resumed_last_date]
                    resume_close = float(df.iloc[i_resume]['close'])
                    portfolio.update_price(symbol, resume_close)
                open_days = new_open_days
                
    except Exception as e:
        print(f"Resume failed, starting from scratch: {e}")
    
    # Processing Loop
    for idx_day, dstr in enumerate(open_days):
        if dstr not in idx_map: continue
        
        # Check stop signal
        if idx_day % 1 == 0:
            try:
                url, key = _supabase_creds()
                if url and key:
                    res = requests.get(
                        f"{url}/rest/v1/runs?run_id=eq.{run_id}&select=status",
                        headers=_supabase_headers(key, False),
                        timeout=5
                    )
                    if res.status_code == 200:
                        rows = res.json()
                        if not rows:
                            print(f"Job {run_id} was deleted from DB. Aborting.")
                            return {'status': 'deleted'}
                        if rows[0]['status'] != 'running':
                            print(f"Job {run_id} stopped externally.")
                            return {'status': 'stopped'}
            except Exception:
                pass

        i = idx_map[dstr]
        date_str = df.iloc[i]['date'].strftime('%Y-%m-%d')
        price = float(df.iloc[i]['close'])
        
        # Update Portfolio Price
        portfolio.update_price(symbol, price)
        
        # Context Window
        start_idx = max(0, i - 90)
        window_df_slice = df.iloc[start_idx:i+1]
        
        # Market Data Construction
        md_one = build_market_data_for_day(symbol, window_df_slice)
        
        # Factors Injection
        # Inject all available technical factors from Tushare (stk_factor)
        factors_to_inject = [
            'macd', 'macd_dif', 'macd_dea',
            'rsi_6', 'rsi_12', 'rsi_24',
            'kdj_k', 'kdj_d', 'kdj_j',
            'boll_upper', 'boll_mid', 'boll_lower',
            'cci', 'vol', 'pct_change'
        ]
        for col in factors_to_inject:
            if col in df.columns:
                val = df.iloc[i][col]
                md_one[f'factor_{col}'] = float(val) if not pd.isna(val) else None

        # Cooldown Logic
        if buy_cooldown_until and dstr < buy_cooldown_until:
            md_one['buy_cooldown'] = True
        else:
            md_one['buy_cooldown'] = False

        # --- Dify TA Request ---
        # ta_text = None
        # try:
        #     daily_in, weekly_in = _fetch_daily_weekly_from_api(pro, ts_code, dstr, 80, 40)
        #     ta_text = _request_technical_analysis_dify_v2(symbol, daily_in, weekly_in)
        #     if ta_text:
        #         md_one['technical_analysis'] = ta_text
        # except:
        #     pass

        # --- LLM Decision ---
        pf_json = portfolio.return_json()
        
        # Inject State
        has_position = symbol in portfolio.positions and portfolio.positions[symbol].quantity != 0
        current_position_lots = 0
        if has_position:
            current_position_lots = int(portfolio.positions[symbol].quantity // lot_size)
            
        # === 修复开始：计算最大可买手数 ===
        fees_rate = commission_rate + (transfer_fee_rate if is_shanghai else 0.0)
        max_buy_lots = 0
        if price > 0 and portfolio.available_cash > 0:
            # 预估最大可买手数 = 可用现金 / (单股价格 * 每手股数 * (1+费率))
            # 增加 1% 滑点缓冲，避免卡边导致买入失败
            est_cost_per_lot = price * 1.01 * lot_size * (1 + fees_rate)
            max_buy_lots = int(portfolio.available_cash // est_cost_per_lot)
        # === 修复结束 ===

        # Generate Recent Actions Text (Memory)
        recent_actions_text = None
        try:
            # Filter only executed trades
            filtered_actions = [
                a for a in actions 
                if str(a.get('signal')).lower() in ('buy', 'sell', 'close') 
                and a.get('success', True) # In simplified core, we assume actions appended are successful or we track them
            ]
            # We need to track actions in the loop. Currently 'actions' list is defined but not populated in core_backtest.py!
            # We need to append to 'actions' list after execution.
            
            last_k = filtered_actions[-5:] # Last 5 trades
            if last_k:
                lines = []
                for a in last_k:
                    q = a.get('quantity', 0)
                    p = a.get('price', 0)
                    s = a.get('signal', '')
                    d = a.get('date', '')
                    lines.append(f"- {d} {s} {q} shares @ {p:.2f}")
                recent_actions_text = "\n".join(lines)
        except Exception:
            pass

        # === 修复开始: 正确计算允许的动作与 T+1 状态 ===
        
        # 1. 计算 T+1 可卖状态
        is_tplus1_locked = False
        if can_sell_after.get(symbol) and dstr < can_sell_after[symbol]:
            is_tplus1_locked = True
        
        # 只要有持仓，且日期满足 T+1，就允许卖出
        can_sell_today = has_position and (not is_tplus1_locked)

        # 2. 构建 allowed_actions
        allowed_actions = ['buy', 'hold']
        if can_sell_today:
            allowed_actions.extend(['sell', 'close'])

        md_one['llm_state'] = {
            'has_position': has_position,
            'is_first_trade': len(actions) == 0,
            'available_cash': float(portfolio.available_cash),
            'current_price': float(price),
            'max_sellable_lots': current_position_lots,
            'max_buyable_lots': max_buy_lots, # 新增字段
            'recent_actions_text': recent_actions_text,
            
            # --- 关键修复字段 ---
            'tplus1_sell_available_today': can_sell_today,
            'allowed_actions': allowed_actions,
            'lot_size': lot_size # 确保 lot_size 传递进去
        }
        # === 修复结束 ===

        # Extract custom system prompt if available
        custom_sys_prompt = strategy_config.get('system_prompt')
        
        decisions = ai_trade_decision_provider(
            {symbol: md_one}, 
            pf_json, 
            model_name=model_name, 
            strategy_prompt=custom_sys_prompt
        )
        decision_obj = decisions.get(symbol, {})
        args = decision_obj.get('trade_signal_args', {}) or {}
        llm_raw = decision_obj.get('_raw_text', '')
        
        # --- Enhanced Logging: Raw Output ---
        print(f"\n[{dstr}] LLM Raw Output:\n{llm_raw}")
        
        signal = str(args.get('signal') or 'hold').lower()
        quantity_lots = int(float(args.get('quantity', 0.0) or 0.0))
        
        # --- Execution Logic (Simplified) ---
        
        # A-Share Limit Rules Check (One-bar limit up/down detection)
        is_limit_up = False
        is_limit_down = False
        limit_threshold = 0.095 # Default 10% (using 9.5% buffer)
        
        # Determine threshold based on symbol
        if symbol.startswith(('688', '300')):
            limit_threshold = 0.195 # 20% (using 19.5% buffer)
            
        try:
            d_open = float(df.iloc[i]['open'])
            d_high = float(df.iloc[i]['high'])
            d_low = float(df.iloc[i]['low'])
            d_close = float(df.iloc[i]['close'])
            
            # Check for Limit Up/Down based on Close Price Change
            # If Close hits limit up, we assume we cannot buy (conservative backtest assumption)
            # If Close hits limit down, we assume we cannot sell
            
            prev_close = float(df.iloc[i-1]['close']) if i > 0 else d_open
            if prev_close > 0:
                chg = (d_close - prev_close) / prev_close
                
                if chg > limit_threshold:
                    is_limit_up = True
                elif chg < -limit_threshold:
                    is_limit_down = True
        except Exception:
            pass

        # Basic validation & Block Reasons
        block_reason = None
        
        if signal == 'buy':
            if is_limit_up:
                signal = 'hold' # Cannot buy on limit up (Close sealed)
                block_reason = "Limit Up (Close Sealed)"
            else:
                fees_rate = commission_rate + (transfer_fee_rate if is_shanghai else 0.0)
                est_cost = price * quantity_lots * lot_size * (1 + fees_rate)
                if est_cost > portfolio.available_cash:
                    old_qty = quantity_lots
                    quantity_lots = int(portfolio.available_cash // (price * lot_size * (1 + fees_rate)))
                    if quantity_lots < old_qty:
                         print(f"[{dstr}] Adjusted Qty: {old_qty} -> {quantity_lots} (Cash Limit)")
                
                if quantity_lots < 1:
                    signal = 'hold'
                    if block_reason is None:
                        block_reason = "Insufficient Cash"
        
        elif signal in ('sell', 'close'):
            if is_limit_down:
                signal = 'hold' # Cannot sell on limit down
                block_reason = "Limit Down (One-bar)"
            elif not has_position:
                signal = 'hold'
                block_reason = "No Position"
            else:
                max_lots = current_position_lots
                if quantity_lots > max_lots or signal == 'close':
                    quantity_lots = max_lots
                if quantity_lots < 1:
                    signal = 'hold'
                    block_reason = "No Sellable Lots"

        # T+1 Check
        if signal in ('sell', 'close'):
            if can_sell_after.get(symbol) and dstr < can_sell_after[symbol]:
                signal = 'hold'
                block_reason = f"T+1 Lock (Can sell after {can_sell_after[symbol]})"

        if block_reason:
            print(f"[{dstr}] 🚫 BLOCKED: {block_reason}")

        # Apply Slippage (0.1% default) & Clamp to High/Low
        # This simulates realistic execution where we likely buy higher and sell lower than close
        slippage_buy = 0.001
        slippage_sell = 0.001
        exec_price = price
        
        try:
            d_high = float(df.iloc[i]['high'])
            d_low = float(df.iloc[i]['low'])
            
            if signal == 'buy':
                exec_price = price * (1 + slippage_buy)
                exec_price = min(exec_price, d_high) # Cannot buy higher than daily high
            elif signal in ('sell', 'close'):
                exec_price = price * (1 - slippage_sell)
                exec_price = max(exec_price, d_low) # Cannot sell lower than daily low
        except Exception:
            pass

        # Execute
        quantity = quantity_lots * lot_size if signal != 'hold' else 0
        # Fix: Use keyword argument for signal to avoid mismatch with profit_target
        ok = portfolio.execute_decision(symbol, quantity, exec_price, 1.0, signal=signal)
        
        if ok:
            print(f"[{dstr}] ✅ EXEC: {signal.upper()} {quantity} @ {exec_price:.2f}")
        elif signal != 'hold':
            print(f"[{dstr}] ❌ EXEC FAIL: {signal.upper()} (Portfolio Rejected)")
        
        # Fees & Cash settlement
        if ok:
            trade_amt = quantity * exec_price
            if signal == 'buy':
                fees = trade_amt * (commission_rate + (transfer_fee_rate if is_shanghai else 0.0))
                portfolio.available_cash -= fees
                # T+1 Set
                try:
                    idx_curr = open_days.index(dstr)
                    if idx_curr + 1 < len(open_days):
                        can_sell_after[symbol] = open_days[idx_curr + 1]
                except: pass
            elif signal in ('sell', 'close'):
                fees = trade_amt * (commission_rate + stamp_duty_rate + (transfer_fee_rate if is_shanghai else 0.0))
                portfolio.available_cash -= fees
            
            # Record action for memory
            actions.append({
                'date': dstr,
                'signal': signal,
                'quantity': quantity,
                'price': price,
                'success': True
            })

        # Always update asset value daily, regardless of trade execution
        portfolio._update_total_asset()

        # --- Record Keeping ---
        
        # Re-generate market prompt for logging purposes
        logged_market_prompt = build_market_prompt(symbol, md_one, pf_json)

        # 1. LLM JSON to R2 (Key: aitrading/{symbol}/{date}/llm_{symbol}.json)
        llm_rec = {
            "date": dstr, # YYYYMMDD
            "symbol": symbol,
            "model_name": model_name,
            "market_prompt": logged_market_prompt,
            "reasoning": decision_obj.get('reasoning', ''),
            "decision": decision_obj
        }
        _r2_upload_data(json.dumps(llm_rec, ensure_ascii=False), 'aitrading', run_id, symbol, dstr, 'json')

        # 2. Supabase Records
        current_pos_qty = portfolio.positions[symbol].quantity if symbol in portfolio.positions else 0
        _supabase_upsert_trade(run_id, symbol, dstr, {
            'signal': signal,
            'quantity': quantity,
            'price': exec_price, # Use actual execution price
            'effective_price': exec_price,
            'cash_after': portfolio.available_cash,
            'position_after': current_pos_qty, # Fix: Use actual portfolio state
            'note': f"success={ok}"
        })
        
        _supabase_upsert_daily_metrics(
            run_id, symbol, dstr, 
            portfolio.available_cash, 
            portfolio.total_asset, 
            portfolio.positions.get(symbol).quantity if symbol in portfolio.positions else 0,
            initial_cash
        )
        
        _supabase_upsert_ohlc(run_id, symbol, dstr, 
            float(df.iloc[i]['open']), float(df.iloc[i]['high']), float(df.iloc[i]['low']), price
        )
        
        _supabase_upsert_checkpoint(run_id, symbol, dstr, 'processed')

    _supabase_update_run_status(run_id, 'completed')
    return {'status': 'success'}