import argparse
import json
import sys
import os

# 添加当前目录到 sys.path 以便导入 core_backtest_v2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core_backtest_v2 import execute_backtest_v2

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run_id', required=True)
    parser.add_argument('--symbol', required=True)
    parser.add_argument('--start', required=True)
    parser.add_argument('--end', required=True)
    parser.add_argument('--config', required=True, help="Path to strategy config JSON file")
    
    args = parser.parse_args()
    
    # 1. Load Config
    try:
        with open(args.config, 'r', encoding='utf-8') as f:
            strategy_config = json.load(f)
    except Exception as e:
        print(json.dumps({"error": f"Failed to load config file: {str(e)}"}))
        sys.exit(1)

    # 2. Execute Backtest
    try:
        # 所有的 print 日志都会被捕获作为 logs 返回给前端
        result = execute_backtest_v2(
            run_id=args.run_id,
            symbol=args.symbol,
            start_date=args.start,
            end_date=args.end,
            strategy_config=strategy_config
        )
        
        # 3. Output Final JSON (Critical for API to parse)
        print(json.dumps(result, ensure_ascii=False))
        
    except Exception as e:
        print(json.dumps({"error": f"Execution Error: {str(e)}"}))
        sys.exit(1)

if __name__ == "__main__":
    main()
