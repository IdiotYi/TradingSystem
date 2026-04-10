from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.backtest_service import run_backtest

router = APIRouter()


class StrategyParams(BaseModel):
    score_rising_days: int = 3
    oversold_std_mult: float = 2.0
    take_profit_pct: float = 0.15
    take_profit_std_mult: float = 1.5
    stop_loss_pct: float = 0.05
    add_position_pct: float = 0.05
    half_position_ratio: float = 0.5
    # 三因子计算参数
    bias_n: int = 20
    momentum_day: int = 20
    slope_n: int = 20
    efficiency_n: int = 20
    zscore_window: int = 60


class BacktestRequest(BaseModel):
    stock_code: str
    start_date: str
    end_date: str
    initial_cash: float = 100000.0
    strategy_params: StrategyParams = StrategyParams()


@router.post("/run")
async def run_backtest_endpoint(request: BacktestRequest):
    try:
        return run_backtest(
            stock_code=request.stock_code,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_cash=request.initial_cash,
            strategy_params=request.strategy_params.model_dump(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"回测失败: {e}")
