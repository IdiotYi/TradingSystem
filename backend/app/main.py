from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import CORS_ORIGINS
from app.api import analysis, backtest, chan, data, fund

app = FastAPI(title="TradingSystem API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
app.include_router(chan.router, prefix="/api/chan", tags=["chan"])
app.include_router(data.router, prefix="/api/data", tags=["data"])
app.include_router(fund.router, prefix="/api/fund", tags=["fund"])

@app.get("/health")
async def health():
    return {"status": "ok"}
