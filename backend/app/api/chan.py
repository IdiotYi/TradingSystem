import traceback
from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.chan_service import analyze_chan
from app.services.minute_data_service import refresh_minute_data

router = APIRouter()


class ChanRequest(BaseModel):
    stock_code: str
    period: Literal["daily", "30", "5"] = "daily"
    start_date: str = "2023-01-01"
    end_date: Optional[str] = None


class ChanRefreshRequest(BaseModel):
    stock_code: str
    period: Literal["30", "5"]


def _raise_chan_http_error(exc: Exception, action: str) -> None:
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    traceback.print_exc()
    raise HTTPException(status_code=500, detail=f"{action}失败: {exc}") from exc


@router.post("/analyze")
async def analyze(req: ChanRequest):
    try:
        return analyze_chan(req.stock_code, req.start_date, req.end_date, req.period)
    except Exception as exc:
        _raise_chan_http_error(exc, "缠论分析")


@router.post("/refresh")
async def refresh(req: ChanRefreshRequest):
    try:
        return refresh_minute_data(req.stock_code, req.period)
    except Exception as exc:
        _raise_chan_http_error(exc, "分钟数据刷新")
