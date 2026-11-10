import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app


def _prices():
    raw = [10.0] * 242 + [20.0, 30.0]
    close = [value / 2 for value in raw]
    return pd.DataFrame({
        '日期': pd.bdate_range('2025-01-01', periods=244).strftime('%Y-%m-%d'),
        '开盘': close, '最高': close, '最低': close, '收盘': close,
        '收盘_未复权': raw, '成交量': [100.0] * 244,
        '成交额': [value * 100 for value in raw],
        '换手率': [1.0] * 242 + [2.0, 3.0],
    })


def test_analysis_maw243_has_full_warmup_and_adjusted_turnover_weighting(monkeypatch):
    monkeypatch.setattr('app.services.indicator_service.load_stock_data', lambda _: _prices())
    response = TestClient(app).post('/api/analysis/run', json={'stock_code': '002156'})
    assert response.status_code == 200
    result = response.json()
    assert len(result['maw243']) == len(result['dates']) == 244
    assert result['maw243'][:242] == [None] * 242
    # 243rd day: (242*10 + 2*20) / (242+2) * 0.5
    # 244th day: remove first day; (241*10 + 2*20 + 3*30) / (241+2+3) * 0.5
    assert result['maw243'][242:] == [5.041, 5.1626]


@pytest.mark.parametrize('missing', ['成交额', '换手率'])
def test_analysis_maw243_is_null_when_required_data_is_missing(monkeypatch, missing):
    monkeypatch.setattr(
        'app.services.indicator_service.load_stock_data', lambda _: _prices().drop(columns=missing),
    )
    response = TestClient(app).post('/api/analysis/run', json={'stock_code': '002156'})
    assert response.status_code == 200
    assert response.json()['maw243'] == [None] * 244


def test_missing_turnover_does_not_hide_adjusted_vwap(monkeypatch):
    monkeypatch.setattr('app.services.indicator_service.load_stock_data',
                        lambda _: _prices().drop(columns='换手率'))
    response = TestClient(app).post('/api/analysis/run', json={'stock_code': '512710'})
    assert response.status_code == 200
    result = response.json()
    assert result['vwap'][-2:] == [10.0, 15.0]
    assert result['maw243'] == [None] * 244
    assert result['indicator_warnings']
