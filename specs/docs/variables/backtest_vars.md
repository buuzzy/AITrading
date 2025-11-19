# backtest.py 变量说明（人话版）

【数据策略】本项目使用 API-only 获取行情与指标，不再读写本地 `data/` 目录；若接口失败会报错。回测生成的结果文件仍存放在 `backtest_data/<symbol>/` 下。

下面这些名字，都是回测时用得到的。尽量说人话，别绕弯子。

## 基本输入
- `symbol`：股票代码（比如 `600895`）。会自动判断是沪/深，内部统一成 `600895.SH` 或 `000001.SZ`。
- `start_date` / `end_date`：回测的起止日期，格式 `YYYYMMDD`，比如 `20250901`。
- `model_name`：用哪个 LLM 模型做决策（默认 `deepseek-chat`）。

## 资金与交易规则
- `initial_cash`：初始资金，默认 `100000.0`。
- `lot_size`：A 股一手的股数，默认 `100`。买入必须按“手”下单。
- `commission_rate`：佣金费率（买卖都收），默认 `0.0003`。
- `stamp_duty_rate`：印花税（只在卖出收），默认 `0.0005`。
- `transfer_fee_rate`：过户费（沪市收，深市不收），默认 `0.00001`。
- `leverage`：杠杆，当前实现固定写到 CSV 里为 `1.0`。

## 输出文件位置
- `output_root`：输出根目录，默认 `backtest_data`。
- `output_layout`：输出布局，默认 `per_symbol`。也就是按股票分目录存档，比如：
  - 文本/JSON：`backtest_data/<symbol>/llm_returns_<start>_<end>.*`
  - 交易 CSV：`backtest_data/<symbol>/trades_<start>_<end>.csv`

## 运行中的关键变量
- `portfolio.available_cash`：当前可用现金。
- `portfolio.total_asset`：当前总资产（现金+持仓按当日收盘价估值）。
- `signal`：模型给出的动作，只允许这几种：`buy`（买入）、`sell`（减仓）、`close`（清仓）、`hold`（不动）。
- `quantity`：数量。对外显示是“股数”，买入会自动按“手”取整（100 股为一手）。
- `success`：是否真的执行了动作（1=执行成功，0=没执行，比如资金不够或 T+1 限制）。
- `llm_ms`：当日 LLM 决策耗时，单位毫秒。

## 写入 CSV 的字段（列）
CSV 每天写一行，表头是（末尾追加一列以不破坏旧逻辑）：
```
date,price,signal,quantity,leverage,success,available_cash,total_asset,llm_ms,effective_price
```
每列是什么意思：
- `date`：当天日期（`YYYY-MM-DD`）。
- `price`：当天收盘价（四位小数）。
- `signal`：动作（`buy`/`sell`/`close`/`hold`）。
- `quantity`：股数（整数）。
- `leverage`：杠杆，默认 `1.00`。
- `success`：是否执行成功（1/0）。
- `available_cash`：当日结束时的可用现金。
- `total_asset`：当日结束时的总资产。
- `llm_ms`：LLM 决策耗时（毫秒）。
- `effective_price`：实际成交价（含滑点）；`buy/sell/close` 为当日执行价格，`hold` 或未成交则等于当日收盘价。

说明：有的 CSV 可能另带一个 `win_rate`（胜率）可选列，那是为了统计方便加的，不影响旧逻辑；可视化只看 `success==1` 的买/卖/平仓行。

## 数据与交易日
- `ts_code`：像 `600895.SH` 这样的标准代码，用来拉取数据。
- `open_days`：本区间内的交易日列表（只在这些日子做决策和写 CSV）。
- `closes`：收盘价序列，用作当日价格输入和简单指标计算。

## 示例：怎么跑
- 单票回测（人手常用）：
  - `python backtest.py --symbol 600895 --start 20250901 --end 20251106`
- 批量回测（从 CSV 读多个标的）：
  - `python backtest.py --stocklist stocklist.csv`

跑完，会在 `backtest_data/600895/` 下看到：
- `llm_returns_*.txt` / `llm_returns_*.ndjson`：模型输出的记录（含思考片段、动作）。
- `trades_*.csv`：每日交易结果（就是上面说的那些列）。

## 常见坑位
- 没有标注：通常是当天 `success=0`（没执行）或动作是 `hold`。
- 买入数量不对：记住是按“手”取整，资金不够也会被砍到能成交的最大手数。
- 卖不出去：A 股 T+1，今天买的明天才能卖；清仓需要有持仓。