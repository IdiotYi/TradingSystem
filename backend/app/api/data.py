from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.data_service import refresh_stock_data

router = APIRouter()


class RefreshRequest(BaseModel):
    stock_code: str


@router.post("/refresh")
async def refresh_data(request: RefreshRequest):
    try:
        return refresh_stock_data(request.stock_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"数据刷新失败: {e}")
