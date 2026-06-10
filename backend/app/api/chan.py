from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.chan_service import analyze_chan

router = APIRouter()


class ChanRequest(BaseModel):
    stock_code: str
    start_date: str = "2023-01-01"
    end_date: Optional[str] = None


@router.post("/analyze")
async def analyze(req: ChanRequest):
    try:
        return analyze_chan(req.stock_code, req.start_date, req.end_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"缠论分析失败: {e}")
