import traceback
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.fund_data_service import FundNotFoundError
from app.services.fund_investment_service import (
    get_fund_analysis,
    refresh_fund,
    run_fund_backtest,
)


router = APIRouter()


class FundCodeRequest(BaseModel):
    fund_code: str


class FundBacktestRequest(BaseModel):
    fund_code: str
    strategy_name: Literal["weekly_investment"] = "weekly_investment"
    start_date: date
    weekday: int = Field(ge=1, le=5)
    amount: float = Field(gt=0)


def _raise_fund_http_error(exc: Exception, action: str) -> None:
    if isinstance(exc, FundNotFoundError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    traceback.print_exc()
    raise HTTPException(status_code=500, detail=f"{action}失败: {exc}") from exc


@router.post("/analysis")
async def analyze_fund(request: FundCodeRequest):
    try:
        return get_fund_analysis(request.fund_code)
    except Exception as exc:
        _raise_fund_http_error(exc, "基金分析")


@router.post("/refresh")
async def refresh_fund_endpoint(request: FundCodeRequest):
    try:
        return refresh_fund(request.fund_code)
    except Exception as exc:
        _raise_fund_http_error(exc, "基金数据刷新")


@router.post("/backtest")
async def backtest_fund(request: FundBacktestRequest):
    try:
        return run_fund_backtest(
            fund_code=request.fund_code,
            strategy_name=request.strategy_name,
            start_date=request.start_date.isoformat(),
            weekday=request.weekday,
            amount=request.amount,
        )
    except Exception as exc:
        _raise_fund_http_error(exc, "基金定投回测")
