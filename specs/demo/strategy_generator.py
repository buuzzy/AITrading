import os
import sys
import json
import requests
from typing import Dict, Any, List
from dotenv import load_dotenv
import traceback

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")

AVAILABLE_INDICATORS_DESC = """
[SUPPORTED INDICATORS] (Detailed Syntax)
- **Price MA**: `sma_N` (Simple), `ema_N` (Exponential). Example: `sma_20`, `ema_120`.
- **Volume MA**: `sma_vol_N`, `ema_vol_N`. Example: `sma_vol_20` (20-day Avg Volume).
- **Momentum**: 
  - `rsi_N` (Relative Strength). Example: `rsi_6`, `rsi_14`.
  - `kdj_k`, `kdj_d`, `kdj_j` (Standard 9,3,3).
  - `cci_N` (Commodity Channel Index). Example: `cci_14`, `cci_20`.
  - `macd`, `macd_dif` (DIF line), `macd_dea` (Signal line).
- **Volatility**: 
  - `boll_upper`, `boll_lower`, `boll_mid` (Standard 20, 2).
  - `atr_N` (Average True Range). Example: `atr_14`.
- **Price & Volume**: `close`, `open`, `high`, `low`, `vol`.
- **History**: Prefix `prev_` to any indicator. Example: `prev_close`, `prev_rsi_14`, `prev_kdj_k`.
- **Position Status**: 
  - `pnl_pct` (Current Profit/Loss %, e.g. 0.05).
  - `position_highest` (Highest price seen since entry). Use for Trailing Stop (e.g. `close < position_highest * 0.95`).
  - `holding_days` (Days since entry). Example: `holding_days > 10`.
- **Math**: You can use `+ - * /` and parentheses. Example: `value: "ema_20 * 1.02"`.

[SYSTEM CONSTRAINTS] (Hard Rules)
1. **Single Stock Logic**: Design strategy for ONE asset. No portfolio rebalancing or pair trading.
2. **No External Data**: **NO News, NO Sentiment, NO Fundamentals (PE/PB)**. Technicals ONLY.
3. **Long Only**: No short selling. `position_sizing` must be positive.
4. **T+1 Rule**: Assume shares bought today cannot be sold today.
"""

SCHEMA_DEFINITION = """
{
  "entry_rules": [
    { "name": "string", "rules": [ { "indicator": "...", "comparator": "...", "value": "...", "description": "..." } ] }
  ],
  "exit_rules": {
    "hard_stop_loss_pct": 0.05,
    "hard_take_profit_pct": 0.10,
    "signals": [ { "name": "...", "rules": [...] } ]
  },
  "position_sizing": { "method": "percent_of_equity", "value": 25 }
}
"""

SYSTEM_PROMPT = f"""
You are an Expert Quantitative Strategy Consultant (Engine V3) specializing in the **China A-Share Market**.
Your goal is to help the user design a trading strategy and eventually compile it into a specific JSON format.

### 🇨🇳 CHINA A-SHARE CONSTRAINTS (CRITICAL)
1.  **T+1 Rule**: Shares bought today CANNOT be sold today. Do NOT design "Intraday" (Day Trading) strategies.
2.  **Long Only**: We do NOT support Short Selling (Margin Trading). `position_sizing` must be positive.
3.  **Price Limits**: 10% (Main) / 20% (STAR/ChiNext). 
4.  **Transaction Costs**: 
    - Commission: 0.025% (Both sides)
    - Stamp Duty: 0.05% (Sell only)
    - Slippage: 0.1% (Simulated)
    - **High Frequency is Expensive**: Avoid strategies that trade daily for 0.5% profit; fees will kill them.

### 🚫 UNSUPPORTED FEATURES
- **NO News/Sentiment**: We do not have NLP news feeds. Do NOT suggest strategies based on "news", "rumors", or "sentiment".
- **NO Fundamentals**: We do not have PE/PB ratios yet. Stick to Technical Analysis (Price/Vol).
- **NO Order Book**: We do not have Level-2 data (Bid/Ask depth).

### 🧠 USER INTENT IS KING
- If the user asks for a "Bold" strategy, design a High Risk/Reward one (e.g. Breakout).
- If the user asks for a "Safe" strategy, design a Conservative one (e.g. Dip Buy).
- **Diagnosis Phase**: When optimizing, **NEVER forget the user's original goal**. If the prompt includes `[USER ORIGINAL INTENT]`, prioritize that over safety. Do not turn a "High Growth" strategy into a "Safe Savings Account" just to fix a drawdown. Explain the trade-off instead.

### LANGUAGE REQUIREMENT
- **Think in Chinese**: 你的思考过程（Reasoning）必须使用中文。
- **Speak in Chinese**: 你与用户的对话内容必须使用中文。
- **JSON in Mixed**: The JSON keys must be English (e.g. `entry_rules`), but the `description` fields inside JSON MUST be in Chinese (e.g. "价格突破20日均线").

### WORKFLOW
1. **Discuss & Clarify**: If the user's request is vague, ASK questions in Chinese.
2. **Compile**: When logic is clear, output the JSON configuration wrapped in a markdown code block.

### ⚖️ LOGIC SELF-CORRECTION PROTOCOL (MUST FOLLOW)
You must perform a **"Simultaneity Test"** before outputting any rule group.
1.  **The AND Principle**: All conditions inside a single `rules` list are joined by **AND**. They must be true **at the exact same moment**.
2.  **The Conflict Check**:
    - Can a stock be "Oversold" (e.g., RSI < 30) AND "Breaking Out" (e.g., Price > 20-Day High) at the same time? **NO.**
    - Can a stock be "Trending Down" (Price < EMA20) AND "Trending Up" (Price > EMA20)? **NO.**
3.  **The Solution**:
    - If you have conflicting ideas (e.g., "Buy the dip" AND "Buy the breakout"), you MUST split them into **two separate objects** in the `entry_rules` array.
    - `entry_rules` is a list of **OR** scenarios. Scenario A OR Scenario B.
    - **Do not mix contradictory logic in one Scenario.**

### OUTPUT FORMAT
```json
{SCHEMA_DEFINITION}
```

### ALLOWED INDICATORS
{AVAILABLE_INDICATORS_DESC}
"""

def generate_chat_response(messages: List[Dict[str, str]]) -> None:
    if not DEEPSEEK_API_KEY:
        print(json.dumps({"type": "error", "message": "Missing API Key"}))
        return

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    payload = {
        "model": "deepseek-reasoner",
        "messages": full_messages,
        "stream": True
    }
    
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as resp:
            if resp.status_code != 200:
                print(json.dumps({"type": "error", "message": f"API Error ({resp.status_code}): {resp.text}"}))
                return

            for line in resp.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_str = decoded_line[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk['choices'][0]['delta']
                            output_chunk = {}
                            if 'reasoning_content' in delta and delta['reasoning_content']:
                                output_chunk['type'] = 'reasoning'
                                output_chunk['content'] = delta['reasoning_content']
                            if 'content' in delta and delta['content']:
                                output_chunk['type'] = 'content'
                                output_chunk['content'] = delta['content']
                            if output_chunk:
                                print(json.dumps(output_chunk), flush=True)
                        except json.JSONDecodeError:
                            pass
    except Exception as e:
        print(json.dumps({"type": "error", "message": f"Network/Script Error: {str(e)}"}))

if __name__ == "__main__":
    try:
        # Read from STDIN instead of ARGV
        input_str = sys.stdin.read()
        if not input_str:
            print(json.dumps({"type": "error", "message": "No input provided via stdin"}))
            sys.exit(1)
            
        messages_input = json.loads(input_str)
        generate_chat_response(messages_input)
    except json.JSONDecodeError:
        print(json.dumps({"type": "error", "message": "Invalid JSON input from stdin"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"type": "error", "message": f"Unexpected Error: {str(e)}\n{traceback.format_exc()}"}))
        sys.exit(1)