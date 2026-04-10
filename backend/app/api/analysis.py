from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.indicator_service import get_analysis_data

router = APIRouter()


class AnalysisRequest(BaseModel):
    stock_code: str


@router.post("/run")
async def run_analysis(request: AnalysisRequest):
    try:
        return get_analysis_data(request.stock_code)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")
