from app.core.fund_investment import (
    run_smart_dip_investment,
    run_weekly_investment,
)
from app.services.fund_data_service import load_fund_data, refresh_fund_data


def get_fund_analysis(fund_code: str) -> dict:
    df = load_fund_data(fund_code)
    latest = df.iloc[-1]
    return {
        "success": True,
        "fund_code": str(latest["基金代码"]),
        "fund_name": str(latest["基金名称"]),
        "fund_type": str(latest["基金类型"]),
        "date_from": df["日期"].iloc[0],
        "date_to": df["日期"].iloc[-1],
        "rows": len(df),
        "latest_nav": round(float(latest["单位净值"]), 6),
    }


def refresh_fund(fund_code: str) -> dict:
    return refresh_fund_data(fund_code)


def run_fund_backtest(
    fund_code: str,
    strategy_name: str,
    start_date: str,
    weekday: int,
    amount: float,
) -> dict:
    if strategy_name == "weekly_investment":
        strategy = run_weekly_investment
    elif strategy_name == "smart_dip_investment":
        strategy = run_smart_dip_investment
    else:
        raise ValueError(f"不支持的基金定投策略: {strategy_name}")

    df = load_fund_data(fund_code)
    result = strategy(df, start_date, weekday, amount)
    return {
        "success": True,
        "fund_code": str(df["基金代码"].iloc[0]),
        **result,
    }
