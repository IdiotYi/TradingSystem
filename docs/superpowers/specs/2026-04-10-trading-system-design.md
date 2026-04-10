# TradingSystem 设计文档

**日期**：2026-04-10  
**状态**：已审批

---

## 1. 项目概述

A股/ETF技术面分析与回测平台。用户输入股票/ETF代码，系统自动加载或下载历史数据，展示技术指标分析结果，并支持三因子动量策略的回测。

---

## 2. 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 19 + TypeScript + ECharts 6 + Ant Design + Axios |
| 后端 | FastAPI + Python + pandas + numpy + akshare |
| 数据 | CSV文件，路径 `data/<code>.csv`，由后端管理 |

---

## 3. 目录结构

```
TradingSystem/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   └── Header.tsx          # 顶部：股票输入 + 分析按钮
│   │   │   ├── technical/
│   │   │   │   ├── TechnicalTab.tsx    # 技术分析 Tab 主容器
│   │   │   │   ├── KLineChart.tsx      # K线 + MA + SuperTrend 图表
│   │   │   │   └── AnalysisCards.tsx   # 百分位 + 最大回撤卡片
│   │   │   └── backtest/
│   │   │       ├── BacktestTab.tsx     # 回测 Tab 主容器
│   │   │       ├── BacktestConfig.tsx  # 参数配置表单
│   │   │       ├── BacktestChart.tsx   # K线 + Score + 买卖标记图表
│   │   │       ├── BacktestSummary.tsx # 汇总卡片（收益/基准/超额/手续费）
│   │   │       └── TradeTable.tsx      # 交易明细表
│   │   ├── services/
│   │   │   └── api.ts                  # axios封装，所有API调用
│   │   ├── types/
│   │   │   ├── stock.ts                # 股票数据类型
│   │   │   └── backtest.ts             # 回测数据类型
│   │   └── App.tsx                     # 根组件，Tab切换逻辑
│   ├── package.json
│   └── tsconfig.json
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI 应用入口，CORS配置
│   │   ├── config.py                   # 配置（端口、数据目录路径等）
│   │   ├── api/
│   │   │   ├── analysis.py             # POST /api/analysis/run
│   │   │   └── backtest.py             # POST /api/backtest/run
│   │   ├── services/
│   │   │   ├── data_service.py         # CSV加载 + akshare下载
│   │   │   ├── indicator_service.py    # MA、SuperTrend、百分位、最大回撤
│   │   │   └── backtest_service.py     # 三因子计算 + 策略执行
│   │   └── core/
│   │       ├── indicators.py           # 纯函数：MA、SuperTrend(10,3)计算
│   │       └── three_factors.py        # 纯函数：三因子score计算
│   ├── requirements.txt
│   └── run.py                          # 启动脚本：uvicorn app.main:app
│
├── data/                               # CSV数据文件，<code>.csv
│
└── docs/
    └── superpowers/specs/
        └── 2026-04-10-trading-system-design.md
```

---

## 4. API 接口

### 4.1 技术分析

```
POST /api/analysis/run
Content-Type: application/json

Request:
{
  "stock_code": "600519"
}

Response:
{
  "success": true,
  "stock_code": "600519",
  "dates": ["2020-01-02", ...],
  "open": [...], "high": [...], "low": [...], "close": [...], "volume": [...],
  "ma5": [...], "ma20": [...], "ma60": [...],
  "supertrend": [...],          // SuperTrend(10,3)值
  "supertrend_direction": [...], // 1=上升趋势, -1=下降趋势
  "current_price": 1800.00,
  "p20": 1200.00,
  "p50": 1500.00,
  "p80": 1900.00,
  "max_drawdown": -0.3245,
  "drawdown_peak_date": "2021-02-18",
  "drawdown_trough_date": "2022-10-31",
  "drawdown_peak_price": 2627.88,
  "drawdown_trough_price": 1775.35
}
```

### 4.2 回测

```
POST /api/backtest/run
Content-Type: application/json

Request:
{
  "stock_code": "600519",
  "start_date": "2023-01-01",
  "end_date": "2026-04-10",
  "initial_cash": 100000,
  "strategy_params": {
    "score_rising_days": 3,       // score连续上升天数（买入条件）
    "oversold_std_mult": 2.0,     // 买入：score < mean - N*std
    "take_profit_pct": 0.15,      // 止盈：盈利达到15%
    "take_profit_std_mult": 1.5,  // 止盈：score > mean + N*std
    "stop_loss_pct": 0.05,        // 止损：亏损达到5%
    "add_position_pct": 0.05,     // 加仓触发：亏损达到5%
    "half_position_ratio": 0.5    // 初始仓位比例（0.5=半仓）
  }
}

Response:
{
  "success": true,
  "dates": [...],
  "close": [...],
  "open": [...], "high": [...], "low": [...],
  "ma5": [...], "ma20": [...], "ma60": [...],
  "supertrend": [...],           // SuperTrend(10,3)值
  "supertrend_direction": [...],  // 1=上升趋势, -1=下降趋势
  "score": [...],
  "score_mean": [...],
  "score_std": [...],
  "trades": [
    {
      "date": "2023-03-15",
      "direction": "买入",
      "reason": "三因子信号",
      "price": 1680.00,
      "shares": 100,
      "amount": 168000.00,
      "transfer_fee": 1.68,
      "commission": 12.60,
      "stamp_tax": null,
      "total_fee": 14.28,
      "pnl": null,
      "remaining_cash": 31985.72
    },
    ...
  ],
  "summary": {
    "initial_cash": 100000,
    "final_assets": 125000,
    "total_return": 0.25,
    "total_fees": 120.50,
    "benchmark_return": 0.18,
    "excess_return": 0.07,
    "final_shares": 0,
    "final_cash": 125000
  }
}
```

---

## 5. UI 布局

### 5.1 整体结构

```
┌─────────────────────────────────────────────────────┐
│  TradingSystem    [股票代码输入框]  [分析按钮]          │  Header
├─────────────────────────────────────────────────────┤
│  [技术分析]  [回测]                                    │  Tabs
├─────────────────────────────────────────────────────┤
│                    Tab 内容区                         │
└─────────────────────────────────────────────────────┘
```

### 5.2 技术分析 Tab

```
┌──────────┬──────────────────────┬──────────────────────┐
│ 当前价格  │  P20 / P50 / P80 百分位│  最大回撤+起止日期+价格│
└──────────┴──────────────────────┴──────────────────────┘
┌─────────────────────────────────────────────────────────┐
│  K线图（红涨绿跌）+ MA5/MA20/MA60 + SuperTrend(10,3)    │
│  ══════════════════ 时间轴拖动 ════════════════════════  │
└─────────────────────────────────────────────────────────┘
```

### 5.3 回测 Tab

```
┌──────────────────────────────────────────────────────────────┐
│  开始日期  结束日期  初始资金(元)  [展开策略参数 ▼]  [运行回测] │
│  ── 展开后 ──────────────────────────────────────────────── │
│  score连升天数  超卖倍数  止盈%  score止盈倍数  止损%  加仓%   │
└──────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│  K线 + MA5/20/60 + SuperTrend  （▲红=买点  ▼绿=卖点）       │
│  ─────────────────────────────────────────────────────────  │
│  Score折线 + score_mean(橙虚线) + ±2σ灰色参考带             │
│  ═════════════════ 联动时间轴 ════════════════════════════  │
└─────────────────────────────────────────────────────────────┘
┌──────────┬──────────┬──────────┬──────────┐
│ 累计收益  │ 基准收益  │  超额收益 │ 总手续费  │
└──────────┴──────────┴──────────┴──────────┘
┌────────────────────────────────────────────────────────────┐
│ 交易明细：日期/方向/原因/价格/数量/金额/过户费/印花税/佣金/盈亏│
└────────────────────────────────────────────────────────────┘
```

---

## 6. 指标计算规格

### 6.1 移动均线 MA
- MA5、MA20、MA60：简单移动平均（SMA），基于收盘价

### 6.2 SuperTrend(10, 3)
- ATR周期 = 10，乘数 = 3
- 上轨 = (High + Low) / 2 + 3 × ATR(10)
- 下轨 = (High + Low) / 2 - 3 × ATR(10)
- 趋势跟踪：收盘价突破上轨转为下降趋势，突破下轨转为上升趋势

### 6.3 价格百分位
- 基于**全量历史数据**（CSV中所有收盘价）计算20/50/80百分位
- 展示当前价格相对历史分布的位置

### 6.4 最大回撤
- 基于**全量历史数据**计算
- 使用累积最大值法：drawdown = (close - cummax) / cummax
- 返回：峰值日期/价格、谷底日期/价格、最大回撤比例

### 6.5 三因子 Score（完整照搬 analysis.py）
- 乖离动量（权重2）：BIAS_N=60, MOMENTUM_DAY=60
- 斜率动量（权重2）：SLOPE_N=60
- 效率动量（权重6）：EFFICIENCY_N=60
- Z-score滚动窗口：ZSCORE_WINDOW=250
- 综合得分：score = (2×z_bias + 2×z_slope + 6×z_eff) / 10
- score_mean / score_std：expanding窗口，shift(1)防未来函数

---

## 7. 手续费计算（照搬 backtest.py）

```
买入手续费 = amount × 0.00001（过户费）+ amount × 0.000075（佣金）
卖出手续费 = amount × 0.00001（过户费）+ amount × 0.0005（印花税）+ amount × 0.000075（佣金）
```

---

## 8. 图表色彩规范

| 元素 | 颜色 |
|------|------|
| 上涨K线 | `#ef5350` 红色 |
| 下跌K线 | `#26a69a` 绿色 |
| MA5 | `#ffffff` 白色 |
| MA20 | `#ffd700` 黄色 |
| MA60 | `#1890ff` 蓝色 |
| SuperTrend 上升段 | `#4caf50` 绿色 |
| SuperTrend 下降段 | `#f44336` 红色 |
| 买点标记 ▲ | `#ef5350` 红色 |
| 卖点标记 ▼ | `#26a69a` 绿色 |
| Score线 | `#1890ff` 蓝色 |
| score_mean | `#fa8c16` 橙色虚线 |
| ±2σ参考带 | `rgba(200,200,200,0.2)` 浅灰填充 |

---

## 9. 数据加载逻辑

```python
# 后端 data_service.py 核心逻辑
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data"

def load_or_download(stock_code: str) -> pd.DataFrame:
    csv_path = DATA_DIR / f"{code}.csv"
    if not csv_path.exists():
        download_via_akshare(code, csv_path)  # 照搬 stock_data_retriever.py 逻辑
    return pd.read_csv(csv_path, encoding="utf-8-sig")
```

数据下载优先级：stock_zh_a_hist → stock_zh_a_daily → fund_etf_hist_sina（照搬参考实现）

---

## 10. 配置

| 项目 | 值 |
|------|----|
| 后端端口 | 8000 |
| 前端端口 | 3000 |
| CORS | http://localhost:3000 |
| 数据目录 | `<project_root>/data/` |
