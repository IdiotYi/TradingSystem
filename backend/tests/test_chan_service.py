import asyncio

import httpx
import pandas as pd
import pytest

from app.core.chan import Bar, detect_fractals, detect_pens, merge_kbars
from app.main import app
from app.services.chan_service import analyze_chan


def make_chan_frame(count: int, with_time: bool) -> pd.DataFrame:
    wave = [10, 12, 14, 13, 11, 9, 8, 10, 13, 15]
    close = [float(wave[i % len(wave)]) for i in range(count)]
    if with_time:
        labels = pd.date_range(
            "2026-07-01 09:30:00", periods=count, freq="5min"
        ).strftime("%Y-%m-%d %H:%M:%S")
        time_column = "时间"
    else:
        labels = pd.date_range(
            "2023-01-01", periods=count, freq="D"
        ).strftime("%Y-%m-%d")
        time_column = "日期"
    return pd.DataFrame({
        time_column: labels,
        "开盘": close,
        "最高": [value + 1 for value in close],
        "最低": [value - 1 for value in close],
        "收盘": close,
        "成交量": [1000.0] * count,
    })


async def _post(path: str, body: dict) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        return await client.post(path, json=body)


def post_json(path: str, body: dict) -> httpx.Response:
    return asyncio.run(_post(path, body))


def test_daily_period_preserves_existing_response_shape(monkeypatch):
    frame = make_chan_frame(40, with_time=False)
    bars = [
        Bar(
            idx=i,
            date=row["日期"],
            high=float(row["最高"]),
            low=float(row["最低"]),
        )
        for i, row in frame.iterrows()
    ]
    merged = merge_kbars(bars)
    expected = [
        (
            pen.start_src_idx,
            pen.end_src_idx,
            pen.start_price,
            pen.end_price,
            pen.direction,
        )
        for pen in detect_pens(merged, detect_fractals(merged), raw_bars=bars)
    ]
    monkeypatch.setattr(
        "app.services.chan_service.load_stock_data",
        lambda code: frame,
    )

    result = analyze_chan("600519", "2023-01-01", "2023-12-31", period="daily")

    assert result["period"] == "daily"
    assert result["dates"] == frame["日期"].tolist()
    assert result["data_source"] == "stock_daily_cache"
    assert result["coverage_from"] == frame["日期"].iloc[0]
    assert result["coverage_to"] == frame["日期"].iloc[-1]
    assert result["response_from"] == frame["日期"].iloc[0]
    assert result["response_to"] == frame["日期"].iloc[-1]
    actual = [
        (
            pen["start_idx"],
            pen["end_idx"],
            pen["start_price"],
            pen["end_price"],
            pen["direction"],
        )
        for pen in result["pens"]
    ]
    assert actual == expected


def test_minute_period_uses_timestamp_column(monkeypatch):
    frame = make_chan_frame(40, with_time=True)
    metadata = {
        "coverage_from": frame["时间"].iloc[0],
        "coverage_to": frame["时间"].iloc[-1],
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr(
        "app.services.chan_service.load_minute_data",
        lambda code, period: (frame, metadata),
    )

    result = analyze_chan(
        "600519",
        "2026-07-01 09:30:00",
        "2026-07-29 15:00:00",
        period="5",
    )

    assert " " in result["dates"][0]
    assert result["period"] == "5"
    assert result["data_source"] == "baostock"
    assert result["response_from"] == frame["时间"].iloc[0]
    assert result["response_to"] == frame["时间"].iloc[-1]


def test_minute_date_only_end_includes_selected_calendar_day(monkeypatch):
    frame = make_chan_frame(40, with_time=True)
    metadata = {
        "coverage_from": frame["时间"].iloc[0],
        "coverage_to": frame["时间"].iloc[-1],
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr(
        "app.services.chan_service.load_minute_data",
        lambda code, period: (frame, metadata),
    )

    result = analyze_chan(
        "600519",
        "2026-07-01",
        "2026-07-01",
        period="5",
    )

    assert result["dates"] == frame["时间"].tolist()
    assert result["response_to"] == "2026-07-01 12:45:00"


def test_minute_timestamp_end_remains_exact(monkeypatch):
    frame = make_chan_frame(40, with_time=True)
    metadata = {
        "coverage_from": frame["时间"].iloc[0],
        "coverage_to": frame["时间"].iloc[-1],
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr(
        "app.services.chan_service.load_minute_data",
        lambda code, period: (frame, metadata),
    )

    result = analyze_chan(
        "600519",
        "2026-07-01 09:30:00",
        "2026-07-01 10:20:00",
        period="5",
    )

    assert result["dates"] == frame["时间"].iloc[:11].tolist()
    assert result["response_to"] == "2026-07-01 10:20:00"


def test_oversized_response_requires_smaller_range(monkeypatch):
    frame = make_chan_frame(20_001, with_time=True)
    metadata = {
        "coverage_from": frame["时间"].iloc[0],
        "coverage_to": frame["时间"].iloc[-1],
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr(
        "app.services.chan_service.load_minute_data",
        lambda code, period: (frame, metadata),
    )

    with pytest.raises(ValueError, match="缩小日期范围"):
        analyze_chan(
            "600519",
            frame["时间"].iloc[0],
            frame["时间"].iloc[-1],
            period="5",
        )


def test_analyze_endpoint_maps_minute_cache_errors_to_400(monkeypatch):
    monkeypatch.setattr(
        "app.api.chan.analyze_chan",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("分钟数据缓存在当前两年窗口内无可用数据，请显式刷新")
        ),
    )

    response = post_json("/api/chan/analyze", {
        "stock_code": "600519",
        "period": "5",
        "start_date": "2026-07-01 09:30:00",
        "end_date": "2026-07-29 15:00:00",
    })

    assert response.status_code == 400
    assert response.json()["detail"] == "分钟数据缓存在当前两年窗口内无可用数据，请显式刷新"


def test_refresh_endpoint_returns_service_payload(monkeypatch):
    payload = {
        "stock_code": "600519",
        "period": "5",
        "rows": 120,
        "coverage_from": "2026-07-01 09:30:00",
        "coverage_to": "2026-07-29 15:00:00",
        "data_source": "baostock",
        "target_coverage_met": True,
    }
    monkeypatch.setattr("app.api.chan.refresh_minute_data", lambda code, period: payload)

    response = post_json("/api/chan/refresh", {"stock_code": "600519", "period": "5"})

    assert response.status_code == 200
    assert response.json() == payload


def test_refresh_endpoint_maps_value_error_to_400(monkeypatch):
    monkeypatch.setattr(
        "app.api.chan.refresh_minute_data",
        lambda code, period: (_ for _ in ()).throw(ValueError("分钟数据刷新失败")),
    )

    response = post_json("/api/chan/refresh", {"stock_code": "600519", "period": "30"})

    assert response.status_code == 400
    assert response.json()["detail"] == "分钟数据刷新失败"


def make_weekly_daily_frame():
    # Each Monday/Wednesday/Friday has deliberately distinct OHLC values.
    rows = []
    wave = [10, 12, 14, 13, 11, 9, 8, 10, 13, 15]
    for week in range(40):
        monday = pd.Timestamp('2026-01-05') + pd.Timedelta(weeks=week)
        base = wave[week % len(wave)]
        for offset, shift in [(0, 0), (2, 1), (4, 2)]:
            rows.append({
                '日期': (monday + pd.Timedelta(days=offset)).strftime('%Y-%m-%d'),
                '开盘': base + shift, '最高': base + shift + 3,
                '最低': base + shift - 2, '收盘': base + shift + 1,
            })
    return pd.DataFrame(rows)


def test_weekly_api_aggregates_daily_ohlc_and_runs_weekly_pens(monkeypatch):
    frame = make_weekly_daily_frame()
    monkeypatch.setattr('app.services.chan_service.load_stock_data', lambda _: frame)
    monkeypatch.setattr('app.services.chan_service.load_minute_data',
                        lambda *args: pytest.fail('Weekly must use daily data'))
    response = post_json('/api/chan/analyze', {
        'stock_code': '002156', 'period': 'weekly',
        'start_date': '2026-01-01', 'end_date': '2026-10-09',
    })
    assert response.status_code == 200, response.text
    result = response.json()
    assert result['period'] == 'weekly'
    assert len(result['dates']) == 40
    assert result['dates'][0] == '2026-01-09'
    assert result['open'][0] == 10
    assert result['high'][0] == 15
    assert result['low'][0] == 8
    assert result['close'][0] == 13
    assert result['data_source'] == 'stock_daily_cache_weekly'
    bars = [Bar(idx=i, date=d, high=h, low=l) for i, (d, h, l) in enumerate(
        zip(result['dates'], result['high'], result['low']))]
    merged = merge_kbars(bars)
    expected = detect_pens(merged, detect_fractals(merged), raw_bars=bars)
    assert expected
    assert [(p['start_idx'], p['end_idx']) for p in result['pens']] == [
        (p.start_src_idx, p.end_src_idx) for p in expected
    ]


def test_weekly_midweek_end_excludes_future_daily_prices(monkeypatch):
    frame = make_weekly_daily_frame()
    frame.loc[frame['日期'] == '2026-03-13', ['最高', '收盘']] = 9999
    monkeypatch.setattr('app.services.chan_service.load_stock_data', lambda _: frame)
    result = analyze_chan('002156', '2026-01-01', '2026-03-11', period='weekly')
    assert len(result['dates']) == 10
    assert result['response_to'] == '2026-03-11'
    assert result['open'][-1] == 15
    assert result['high'][-1] == 19
    assert result['low'][-1] == 13
    assert result['close'][-1] == 17


def test_weekly_uses_actual_last_trading_day_and_skips_empty_weeks(monkeypatch):
    frame = make_weekly_daily_frame()
    frame = frame.loc[~frame['日期'].isin(['2026-01-09', '2026-01-12', '2026-01-14', '2026-01-16'])]
    monkeypatch.setattr('app.services.chan_service.load_stock_data', lambda _: frame.iloc[::-1])
    result = analyze_chan('002156', '2026-01-01', '2026-10-09', period='weekly')
    assert len(result['dates']) == 39
    assert result['dates'][:2] == ['2026-01-07', '2026-01-23']
    assert result['open'][0] == 10
    assert result['close'][0] == 12


def test_weekly_requires_ten_weekly_bars_not_ten_daily_bars(monkeypatch):
    monkeypatch.setattr('app.services.chan_service.load_stock_data', lambda _: make_weekly_daily_frame())
    response = post_json('/api/chan/analyze', {
        'stock_code': '002156', 'period': 'weekly',
        'start_date': '2026-01-01', 'end_date': '2026-01-30',
    })
    assert response.status_code == 400
    assert '4' in response.json()['detail']


def test_weekly_cannot_be_sent_to_minute_refresh_endpoint():
    response = post_json('/api/chan/refresh', {'stock_code': '002156', 'period': 'weekly'})
    assert response.status_code == 422
