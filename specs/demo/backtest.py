"""
最小回测脚手架：单标的、日线数据、LLM 决策、组合执行

用法：
  source venv/bin/activate
  python backtest.py --symbol 600519 --start 20240101 --end 20241231
  python specs/demo/backtest.py --stocklist stocklist.csv --model deepseek-reasoner

说明：
- 历史数据来源：tinyshare（仅使用在线 pro.stk_factor，失败直接报错退出，不再回退本地缓存）
- 环境变量：需要 `.env` 中存在 `DEEPSEEK_API_KEY` 与 `TINYSHARE_TOKEN`
- 决策引擎：DeepSeek（OpenAI SDK，base_url 指向 deepseek），连续失败3次后暂停并等待用户确认继续或退出
"""
import argparse
import logging
import sys
import os
import uuid
import pandas as pd

# Add root directory to sys.path to allow importing core_backtest
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

from core_backtest import execute_backtest_job, normalize_symbol

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--symbol', required=False, help='股票代码（不含交易所后缀）例如 600519')
    parser.add_argument('--stocklist', required=False, help='CSV 文件路径')
    parser.add_argument('--start', help='开始日期 YYYYMMDD')
    parser.add_argument('--end', help='结束日期 YYYYMMDD（缺省为今天）')
    parser.add_argument('--cash', type=float, default=100000.0)
    parser.add_argument('--model', default='deepseek-chat')
    
    args = parser.parse_args()
    
    # Default end date
    end_date = args.end
    if not end_date:
        end_date = pd.Timestamp.now().strftime('%Y%m%d')

    # Config object mapping
    config = {
        'initial_cash': args.cash,
        'model_name': args.model,
        # Add other defaults if needed
    }

    task_completed = False
    try:
        if args.stocklist:
            print("Stocklist batch mode not fully ported to new core yet. Running loop...")
            try:
                # Force read as string to avoid NaT/Timestamp auto-conversion issues
                df = pd.read_csv(args.stocklist, dtype=str)
                # Normalize columns
                df.columns = [c.strip().lower() for c in df.columns]
                
                if 'stock_code' not in df.columns or 'start_date' not in df.columns:
                    print(f"Error: CSV must contain 'stock_code' and 'start_date'. Found: {df.columns.tolist()}")
                    return

                for i, row in df.iterrows():
                    # Normalize symbol
                    raw_sym = row.get('stock_code')
                    if pd.isna(raw_sym): continue
                    sym = str(raw_sym).split('.')[0].strip()
                    
                    # Normalize start date
                    raw_st = row.get('start_date')
                    if pd.isna(raw_st): continue
                    st = str(raw_st).replace('-', '').split(' ')[0].strip()
                    
                    # Normalize end date
                    raw_ed = row.get('end_date')
                    if pd.isna(raw_ed) or str(raw_ed).lower() == 'nan':
                        ed = end_date
                    else:
                        ed = str(raw_ed).replace('-', '').split(' ')[0].strip()
                    
                    if not sym or not st: continue

                    run_id = str(uuid.uuid4())
                    print(f"[{i+1}/{len(df)}] Running {sym} ({st}-{ed})...")
                    res = execute_backtest_job(run_id, sym, st, ed, config)
                    print(f"Result: {res}")
            except Exception as e:
                print(f"Batch error: {e}")
            task_completed = True
        elif args.symbol and args.start:
            run_id = str(uuid.uuid4())
            print(f"Starting Manual Run: {run_id}")
            execute_backtest_job(run_id, args.symbol, args.start, end_date, config)
            task_completed = True
        else:
            print("Usage: python backtest.py --symbol ... --start ...")
            task_completed = True
    except KeyboardInterrupt:
        if not task_completed:
            print("\nTask interrupted.")
            sys.exit(0)

if __name__ == '__main__':
    main()