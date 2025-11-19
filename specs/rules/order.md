以 20251112 为例（A 股模拟实盘三段式工作流）。

# 盘前生成计划
执行计划生成（可选指定模型）：

## 盘前（指定日期）
python3 livetrade.py --date 20251112 --model deepseek-reasoner

## - 盘前（不指定日期，自动最近开放日）
python3 livetrade.py --model deepseek-reasoner


# 盘中手动交易
人工在同日盘中执行，并记录至：`Live/manual_exec/20251112.csv`。

CSV 列定义（表头，严格按此顺序）：
- `ts_code`：股票代码，含交易所后缀，如 `600519.SH`、`000001.SZ`
- `date_T`：交易日，`YYYYMMDD`
- `signal`：`buy/sell/close/hold`
- `quantity_shares`：股数（>=0，卖出/平仓为减仓股数）
- `effective_price`：实际成交价（元），`hold` 或未成交可填收盘价或留空
- `success`：布尔，`true/false`，表示是否成交成功

示例（成功与失败混合）：
ts_code,date_T,signal,quantity_shares,effective_price,success
688981.SH,20251112,buy,100,12.34,true
688981.SH,20251112,sell,100,,false
300465.SZ,20251112,hold,0,28.90,false

# 盘后入账记录
将同日成交入账 + 写交易记录摘要：

## 盘后入账（指定日期，与 CSV 对齐）
python3 livetrade.py --date 20251112 --manual-exec-file Live/manual_exec/20251112.csv --model deepseek-reasoner

## 盘后入账（不指定日期，前提：CSV 的 date_T 就是最近开放日）
python3 livetrade.py --manual-exec-file Live/manual_exec/20251112.csv --model deepseek-reasoner

## 说明
执行侧 T+1 合规（硬阻断）：
- 当 `date_T < can_sell_after` 时，所有 `sell/close` 视为当日不可卖出，标记失败并不记账。
- 失败原因会写入错误日志，且在次日提示词的“RECENT EXECUTIONS”摘要中以 `failed` 展示。

提示词与状态约束：
- `make_llm_state()` 会根据当日可卖性收紧 `allowed_actions`，当日不可卖出则移除 `sell/close`，避免模型越权。
- 注入上一日（含失败）执行摘要：`load_recent_exec()` 将最近 5 条记录整合为文本并注入 `llm_state.recent_actions_text`，供次日 T+2 决策参考。

账户与预算：
- 全局账户状态文件：`Live/account_state.json`，包含 `initial_cash/available_cash/positions`；计划阶段仅读取，入账阶段写回。
- 预算分配：`LIVE_CASH_ALLOCATION=equal`（默认）按等额分配到 `livetrading_stocklist.csv` 的各标的；`fraction/full` 可选（见 README）。

常用模型设置：
- 通过环境变量设置默认模型：`export LLM_MODEL=deepseek-reasoner`；命令行 `--model` 优先级更高。

注意事项：
- 手动成交优先于计划纸面成交；同一个交易日内，成功的人工成交将写入账户状态与交易记录，计划仅用于参考。
- 重跑安全：`open_plan_*.csv` 写入具备主键去重；`llm_reasoner_*.ndjson` 采用逐行追加（含 `timestamp`）。
- 当日不可卖出会被硬阻断且标记失败；次日（满足 T+1）可正常卖出。