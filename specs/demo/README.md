# Alpha-Arena-Lite（A股回测）

A 股历史数据回测平台（LLM 决策，T+1 规则，API-only）。

## 快速开始（回测）

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量（.env）

```env
DEEPSEEK_API_KEY=your-deepseek-api-key
TINYSHARE_TOKEN=your-tinyshare-token
DIFY_API_KEY=your-dify-api-key # 可选：用于 livetrade 集成外部技术分析
```

可选：`LLM_MODEL=deepseek-chat`（默认），或设置你使用的兼容模型名称。

### 3. 运行回测

```bash
python backtest.py --symbol 600519 --start 20240101 --end 20241231
```

输出结果位于 `backtest/<symbol>/`：
- `trades_<symbol>_<start>_<end>.csv`（含费用、成功标记、买卖点）
- `llm_returns_<symbol>_<start>_<end>.ndjson` 与 `.txt`（审计与思考过程）
- `kline_<start>_<end>.html`（交互式K线，标注买卖点）

## 数据策略（API-only）
- 仅使用在线接口获取市场数据与因子，不读写本地 `data/` 缓存。
- 接口失败将报错并跳过该日，不做本地兜底，以保证策略一致性。
- 需要有效 `TINYSHARE_TOKEN` 才能拉取 A 股数据。

## 其他说明
- 项目已移除加密实时仿真与组合快照（`simulation.py`、`hyperliquid_market_data.py`、`portfolio*.json`）。
- 依赖已精简，删除了 `ccxt`、`stockstats`、`openai-agents`，保留 `tinyshare`、`openai`、`pandas`、`numpy`、`plotly`、`python-dotenv`。

## 架构
- 市场数据层：通过 TinyShare（兼容 Tushare）的 `stk_factor/daily` 在线接口获取日线与技术指标；API-only，不使用本地缓存目录。
- 组合管理：`simple_portfolio.py` 实现 A 股约束（按手交易、沪市过户费、卖出印花税、仅做多、T+1 卖出）。
- 决策引擎：`trade_decision_simple_AI.py` 使用 DeepSeek（OpenAI SDK），提示词内嵌约束，支持 `LLM_MODEL` 选择。
- 回测引擎：`backtest.py` 负责数据拉取、逐日迭代、决策执行与结果写盘；支持 `--stocklist` 批量回测。
- 可视化：`visualization.py` 生成交互式 K 线图并标注成功的买卖点。

## 模拟实盘（Live）工作流
- 盘前计划：`python3 livetrade.py --date YYYYMMDD --model deepseek-reasoner`
- 盘中手动成交：编辑 `Live/manual_exec/YYYYMMDD.csv`
  - CSV 表头：`ts_code,date_T,signal,quantity_shares,effective_price,success`
  - 示例：`688981.SH,20251112,buy,100,12.34,true` / `688981.SH,20251112,sell,100,,false`
- 盘后入账与记录：
  - `python3 livetrade.py --date YYYYMMDD --manual-exec-file Live/manual_exec/YYYYMMDD.csv --model deepseek-reasoner`
  - 写回 `Live/account_state.json` 与 `Live/<symbol>/trade_record_<symbol>.csv`
  - 计划文件与审计：`Live/<symbol>/open_plan_*.csv`、`llm_reasoner_*.ndjson`

### 合规与约束（已在代码中落实）
- 当日 T+1 硬阻断：`date_T < can_sell_after` 时，`sell/close` 标记失败且不入账。
- 模型允许动作收紧：`make_llm_state()` 根据可卖性动态收紧 `allowed_actions`；不可卖出时移除 `sell/close`。
- 上一日执行摘要注入：`load_recent_exec()` 注入最近 5 条 `success/failed` 执行到次日提示词。
- 预算分配：`Live/account_state.json` 中的 `available_cash` 按 `LIVE_CASH_ALLOCATION` 分配到各标的（默认 `equal`）。

### 模型与环境变量
- 默认模型可通过环境变量设置：`export LLM_MODEL=deepseek-reasoner`
- 指定模型优先级：命令行 `--model` 高于环境变量。
- 外部技术分析：需设置 `DIFY_API_KEY`（可选）。

## 测试
- 当前项目不包含 `test/` 目录；后续如需引入单元测试，将遵循 A 股规则（按手、三费率、T+1、部分减仓）。

## 文件结构（精简版）
- `backtest.py`：主回测脚本（单标/批量）。
- `simple_portfolio.py`：组合与持仓管理（T+1/费用/按手）。
- `trade_decision_simple_AI.py`：LLM 决策引擎与提示词构建。
- `visualization.py`：K 线可视化与买卖点标注。
- `stocklist.csv`：批量回测清单（`stock_code,start_date,end_date`）。
- `todo.md`：项目优化进度与变更记录（根目录）。
- `README.md`：统一的使用说明、架构与进度提炼。
 - `livetrade.py`：模拟实盘脚本（计划、手动成交入账、审计与合规）。
 - `Live/`：账户状态与交易记录目录（`account_state.json`、`<symbol>/trade_record_*.csv`、`manual_exec/*.csv`）。

## 路线图（提炼）
- 已完成：
  - A 股回测主干（API-only）、费用与 T+1 约束、批量模式与代码规范化。
  - 审计与持久化（`llm_returns.*`、`trades_*.csv`）、K 线可视化。
  - 依赖与文档清理，删除加密实时仿真路径。
- 进行中：
  - 单元测试补齐（按手/三费率/T+1/部分减仓）。
  - 指标与提示词一致性进一步优化（RSI/MACD/EMA 展示与窗口语义）。
- 计划：
  - 生成报告（收益曲线、最大回撤、Sharpe 等）。