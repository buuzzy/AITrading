import uuid
import json
import sys
import os

# 确保能找到 core_backtest_v2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core_backtest_v2 import execute_backtest_v2

# 你的“完美策略” JSON
strategy_json = {
  "entry_rules": [
    {
      "name": "Bear Trap (Fear Opportunity)",
      "rules": [
        {
          "indicator": "rsi_12",
          "comparator": "<",
          "value": 30,
          "description": "Extreme fear/oversold condition"
        },
        {
          "indicator": "close",
          "comparator": "<= ",
          "value": "boll_lower",
          "description": "Price touches or pierces lower Bollinger Band"
        }
      ]
    },
    {
      "name": "Super Trend Pyramiding",
      "rules": [
        {
          "indicator": "close",
          "comparator": ">",
          "value": "ema_10",
          "description": "Price above EMA10"
        },
        {
          "indicator": "ema_10",
          "comparator": ">",
          "value": "ema_20",
          "description": "EMA10 > EMA20"
        },
        {
          "indicator": "macd",
          "comparator": ">",
          "value": 0,
          "description": "MACD positive"
        },
        {
          "indicator": "rsi_12",
          "comparator": "<",
          "value": 85,
          "description": "RSI not overheated"
        }
      ]
    }
  ],
  "exit_rules": {
    "hard_stop_loss_pct": 0.08,
    "hard_take_profit_pct": 0.2,
    "signals": [
      {
        "name": "Trend Break (Conditional)",
        "rules": [
          {
            "indicator": "close",
            "comparator": "<",
            "value": "ema_20",
            "description": "Price breaks below EMA20"
          },
          {
            "indicator": "pnl_pct",
            "comparator": ">",
            "value": 0.1, 
            "description": "ONLY exit if Profit > 10%"
          }
        ]
      },
      {
        "name": "Bull Trap",
        "rules": [
          { "indicator": "rsi_12", "comparator": ">", "value": 80 },
          { "indicator": "macd", "comparator": "<", "value": 0 }
        ]
      },
      {
        "name": "Profit Taking",
        "rules": [
          { "indicator": "pnl_pct", "comparator": ">", "value": 0.15 },
          { "indicator": "macd", "comparator": "<", "value": 0 }
        ]
      }
    ]
  },
  "position_sizing": {
    "method": "percent_of_equity",
    "value": 20
  }
}

# 模拟任务参数 (张江高科)
run_id = str(uuid.uuid4())
symbol = "600895" 
start_date = "20210101" # 拉长周期看效果
end_date = "20250601"

print(f"--- 开始演示 V2.5 策略 (张江高科 600895) ---")
try:
    result = execute_backtest_v2(
        run_id=run_id,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        strategy_config=strategy_json
    )
    print("\n--- 最终结果 ---")
    print(f"Final Equity: {result.get('final_equity')}")
except Exception as e:
    print(f"运行出错: {e}")
