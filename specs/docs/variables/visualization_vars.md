# visualization.py 变量说明（人话版）

【数据策略】本项目已切换为 API-only：不再使用或写入本地 `data/` 缓存目录，所有行情数据均通过接口获取；接口不可用时直接报错并提示。

这个脚本负责画 K 线，并把“成功执行的买/卖/平仓点”标到图上。

## 输入参数（命令行）
- `--trades`：交易 CSV 路径（强烈建议传）。例如：
  - `backtest_data/600895/trades_600895_20250901_20251106.csv`
- `--symbol`、`--start`、`--end`：如果没传 `--trades`，就用这三个参数自己拉数据画纯 K 线。
- `--output`：输出的 HTML 文件路径（不传则按默认位置生成）。
- `--output-root`：输出根目录，默认 `backtest_data`。

## 市场数据（OHLC）
- 从 tinyshare 拉日线，拿到这几列：
  - `trade_date`：日期。
  - `open`：开盘价。
  - `high`：最高价。
  - `low`：最低价。
  - `close`：收盘价。
（不再回退本地缓存）

## 交易数据（来自 CSV）
- 只保留“成功执行”的动作用来画点：`success == 1`，并且 `signal ∈ {buy, sell, close}`。
- 优先使用 `effective_price` 作为标注价格（实际成交价，含滑点）；若该列不存在则回退到 `price`（当日收盘价）。
- 用到的列：`date, price, marker_price, signal, quantity`（其中 `marker_price` 是上述选择的标注价格）。
- 标注文字：
  - 买入：`B <数量>`，绿色三角。
  - 卖出：`S <数量>`，橙色倒三角。
  - 平仓：`C <数量>`，红色叉号。

## 文件名解析（不传 symbol 的情况）
- 支持两种命名：
  - `trades_<symbol>_<start>_<end>.csv`
  - `backtest_data/<symbol>/trades_<start>_<end>.csv`（symbol 从父目录名推出来）

## 怎么用（示例）
- 带交易标注的 K 线：
  - `python visualization.py --trades backtest/600895/trades_600895_20250901_20251106.csv --output backtest/600895/kline_20250901_20251106.html`
- 只画 K 线（不带标注）：
  - `python visualization.py --symbol 600895 --start 20250901 --end 20251106`

## 预览建议
- 用浏览器访问 `http://localhost:8000/...` 或 `http://localhost:8001/...`，不要用 `file:///...`。
- 原因：部分浏览器会限制 `file:///` 加载外部脚本（比如 Plotly 的 CDN），导致图能显示但标注没正常工作。
- python -m http.server 8000
- open backtest/688209/kline_20250901_20251031.html

## 常见坑位与排查
- 没有买卖标注：检查 CSV 是否真的有 `success==1` 的 `buy/sell/close` 行。
- 日期错位：交易日期要和日线的 `trade_date` 对得上；否则点会偏移或不显示。
- 路径不匹配：`--trades` 文件名不符合约定，脚本解析不到 symbol/start/end。