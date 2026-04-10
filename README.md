# TradingSystem

A-股 / ETF 技术分析与回测平台。输入股票代码即可查看技术指标分析，并通过三因子动量策略进行历史回测。

## 功能

- **技术分析**：K线图（ECharts）、MA5/MA20/MA60、SuperTrend 趋势指标
- **三因子动量策略回测**：乖离动量 + 斜率动量 + 效率动量，Z-score 标准化后综合打分
- **回测引擎**：支持半仓建仓、加仓、止盈/止损，含 A 股真实手续费（过户费 + 印花税 + 佣金）
- **参数可调**：策略参数与因子计算参数均可在 UI 中自定义
- **数据刷新**：一键强制重新下载最新行情数据（通过新浪财经，fallback 到东方财富）

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

历史行情数据通过 [akshare](https://akshare.akfamily.xyz/) 自动下载并缓存到本地 `data/` 目录（已排除在版本控制之外）。数据来源：新浪财经（前复权）。
