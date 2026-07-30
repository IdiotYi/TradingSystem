# TradingSystem

A-股 / ETF 技术分析与回测平台，同时支持基金定投分析。股票/ETF 模式提供技术分析与三因子动量回测；基金模式提供基金净值分析、周定投回测与事件明细。

## 功能

- **技术分析**：K线图（ECharts）、MA5/MA20/MA60、SuperTrend 趋势指标
- **三因子动量策略回测**：乖离动量 + 斜率动量 + 效率动量，Z-score 标准化后综合打分
- **基金定投**：支持基金净值分析、周定投回测、累计投入/资产曲线、定投/分红/拆分事件明细
- **回测引擎**：支持半仓建仓、加仓、止盈/止损，含 A 股真实手续费（过户费 + 印花税 + 佣金）
- **参数可调**：策略参数与因子计算参数均可在 UI 中自定义
- **数据刷新**：股票/ETF 支持一键强制重新下载最新行情（通过新浪财经，fallback 到东方财富）；基金模式刷新完整净值、分红与拆分历史

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python · FastAPI · akshare · pandas · scikit-learn |
| 前端 | React 18 · TypeScript · Vite · Ant Design 5 · ECharts |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

浏览器访问 http://localhost:5173

## 使用说明

1. 在顶部搜索框输入股票/ETF 代码（如 `600519`、`159740`），点击**分析**
2. **技术分析**标签页展示 K 线、移动均线和 SuperTrend 指标
3. 切换到**回测**标签页，设置起止日期、初始资金和策略参数，点击**运行回测**
4. 点击**刷新数据**按钮可强制从网络重新下载最新行情（首次查询时会自动下载）

### 基金定投工作流

1. 切换到 **基金定投** 标签页，输入 6 位基金代码（如 `000001`）后点击**分析**
2. 后端会按完整历史净值自动下载并缓存基金数据，文件名为 `data/Fund_<code>.csv`；例如 `data/Fund_000001.csv`
3. 分析结果返回基金名称、基金类型、净值起止日期、总行数和最新单位净值
4. 运行回测时目前仅支持 `weekly_investment` 策略：选择开始日期、工作日（周一到周五）和每周定投金额
5. 若目标定投日缺少净值，系统会只在**同一自然周内向前回退到最近可用净值日**；若该周目标日前没有可用净值，则该周跳过，不会跨周回补
6. 同日事件按 **份额拆分 → 现金分红再投资 → 当期定投** 顺序处理，因此事件明细可重建最终持有份额
7. 分红默认按当日单位净值再投资，份额拆分按拆分比例调整持仓；两者不会增加用户 `total_invested`

### 基金定投范围与限制

- 仅支持有**日单位净值**且通过基金类型校验的公募基金
- 不支持货币基金
- 不支持被基金类型校验识别为 ETF / 场内 / 交易型开放式 / 上市开放式 的基金净值定投回测
- 基金定投默认忽略申购费、赎回费和其他费率
- 基金接口不会返回股票/ETF 使用的 OHLC（开高低收）字段

## 三因子策略说明

| 因子 | 含义 |
|---|---|
| 乖离动量 | 收盘价相对移动均线的偏离趋势斜率 |
| 斜率动量 | 价格归一化后的线性回归斜率 × R² |
| 效率动量 | 净移动距离 / 总波动路径 × 对数动量 |

三个因子经滚动 Z-score 标准化后按 2:2:6 加权合成综合得分 `score`。

**买入条件**（同时满足）：
- `score` 连续 N 日上升
- 近 N 日中任意一日 `score < score_mean − k × score_std`（超卖信号）

**卖出条件**（满足任意一个）：
- 持仓盈利 ≥ 止盈阈值
- `score > score_mean + k × score_std`（超买信号）
- 全仓亏损 ≥ 止损阈值

## 项目结构

```
TradingSystem/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI 路由（analysis / backtest / data）
│   │   ├── core/         # 指标计算（SuperTrend、三因子）
│   │   ├── services/     # 业务逻辑（数据加载、回测引擎）
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/   # Header / KLineChart / BacktestChart 等
│       ├── services/     # axios API 客户端
│       └── types/        # TypeScript 类型定义
└── docs/
```

## 数据说明

历史行情数据通过 [akshare](https://akshare.akfamily.xyz/) 自动下载并缓存到本地 `data/` 目录（已排除在版本控制之外）。

- 股票 / ETF：缓存为 `data/<code>.csv`，数据来源为新浪财经（前复权），失败时 fallback 到东方财富 / 新浪 ETF 接口
- 基金：缓存为 `data/Fund_<code>.csv`，包含净值、分红和拆分归一化后的完整历史记录
