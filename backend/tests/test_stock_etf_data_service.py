import pandas as pd
import pytest

from app.services import data_service
from app.services.indicator_service import get_analysis_data
from app.core.indicators import calc_maw


@pytest.mark.parametrize(('code', 'symbol'), [
    ('512710', 'sh512710'), ('sh512710', 'sh512710'),
    ('159740', 'sz159740'), ('600519', 'sh600519'),
])
def test_sina_fallback_uses_correct_exchange_and_caches_ohlc(monkeypatch, tmp_path, code, symbol):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_daily', lambda **kwargs: pd.DataFrame())
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_hist', lambda **kwargs: pd.DataFrame())
    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_em', lambda **kwargs: pd.DataFrame())

    def provider(**kwargs):
        if kwargs['symbol'] != symbol:
            return pd.DataFrame()
        return pd.DataFrame({
            'date': ['2026-11-02', '2026-11-03'],
            'open': [1.0, 1.1], 'high': [1.2, 1.3], 'low': [0.9, 1.0],
            'close': [1.1, 1.2], 'volume': [10000, 20000], 'amount': [11000, 24000],
        })

    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_sina', provider)
    result = data_service.load_stock_data(code)
    assert result['日期'].tolist() == ['2026-11-02', '2026-11-03']
    assert result['收盘'].tolist() == [1.1, 1.2]
    assert result['最高'].tolist() == [1.2, 1.3]
    assert result['成交额'].tolist() == [11000, 24000]
    assert (tmp_path / f'{symbol[2:]}.csv').exists()

    # A cached ETF must remain readable without downloading again.
    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_sina',
                        lambda **kwargs: pytest.fail('Unexpected cache download'))
    pd.testing.assert_frame_equal(data_service.load_stock_data(code), result)


def eastmoney_frame():
    return pd.DataFrame({
        '日期': pd.bdate_range('2025-01-01', periods=244).strftime('%Y-%m-%d'),
        '股票代码': ['159740'] * 244,
        '开盘': [0.5] * 244, '收盘': [0.5] * 244,
        '最高': [0.52] * 244, '最低': [0.48] * 244,
        # 100 lots = 10,000 shares; 5,000 yuan / 10,000 shares = 0.5 yuan.
        '成交量': [100] * 244, '成交额': [5000] * 244,
        '振幅': [8.0] * 244, '涨跌幅': [0.0] * 244,
        '涨跌额': [0.0] * 244, '换手率': [1.0] * 244,
    })


def test_legacy_eastmoney_cache_uses_share_units_for_chart_and_strategy(monkeypatch, tmp_path):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    path = tmp_path / '159740.csv'
    eastmoney_frame().to_csv(path, index=False, encoding='utf-8-sig')
    original = path.read_bytes()
    result = get_analysis_data('159740')
    assert result['vwap'][-1] == 0.5
    assert result['maw5'][-1] == 0.5
    assert result['maw243'][-1] == 0.5
    assert result['close'][-1] == 0.5
    assert result['volume'][-1] == 10000
    for _ in range(2):
        loaded = data_service.load_stock_data('159740')
        assert loaded['成交量'].iloc[-1] == 10000
        assert calc_maw(loaded, 20).iloc[-1] == 0.5
    assert path.read_bytes() == original


def test_new_eastmoney_download_normalizes_once_and_marks_cached_units(monkeypatch, tmp_path):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_daily', lambda **kwargs: pd.DataFrame())
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_hist', lambda **kwargs: eastmoney_frame())
    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_em', lambda **kwargs: eastmoney_frame())
    first = data_service.load_stock_data('159740')
    cached = pd.read_csv(tmp_path / '159740.csv')
    assert cached['成交量'].iloc[-1] == 10000
    assert first['成交量'].iloc[-1] == 10000
    second = data_service.load_stock_data('159740')
    assert second['成交量'].iloc[-1] == 10000
    assert get_analysis_data('159740')['maw243'][-1] == 0.5


def test_sina_share_volume_is_not_multiplied(monkeypatch, tmp_path):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    frame = eastmoney_frame().drop(columns=['振幅', '涨跌幅', '涨跌额'])
    frame['成交量'] = 10000
    frame.to_csv(tmp_path / '159740.csv', index=False, encoding='utf-8-sig')
    assert data_service.load_stock_data('159740')['成交量'].iloc[-1] == 10000
    assert get_analysis_data('159740')['maw243'][-1] == 0.5


def test_etf_uses_etf_eastmoney_endpoint_for_maw(monkeypatch, tmp_path):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_daily', lambda **kwargs: pd.DataFrame())
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_hist',
                        lambda **kwargs: pytest.fail('ETF must use ETF history endpoint'))
    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_sina',
                        lambda **kwargs: pytest.fail('Complete ETF history is already available'))
    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_em', lambda **kwargs: eastmoney_frame().assign(股票代码='512710'))
    result = get_analysis_data('512710')
    assert result['vwap'][-1] == 0.5
    assert result['maw243'][-1] == 0.5


def test_legacy_sina_amount_supports_vwap_without_inventing_turnover(monkeypatch, tmp_path):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    frame = eastmoney_frame().drop(columns=['振幅', '涨跌幅', '涨跌额', '换手率'])
    frame['成交量'] = 10000
    frame.rename(columns={'成交额': 'amount'}).to_csv(tmp_path / '512710.csv', index=False, encoding='utf-8-sig')
    result = get_analysis_data('512710')
    assert result['vwap'][-1] == 0.5
    assert all(value is None for value in result['maw5'])
    assert result['indicator_warnings']


def test_etf_eastmoney_vwap_uses_same_adjustment_as_candles(monkeypatch, tmp_path):
    monkeypatch.setattr(data_service, 'DATA_DIR', tmp_path)
    monkeypatch.setattr(data_service.ak, 'stock_zh_a_daily', lambda **kwargs: pd.DataFrame())

    def history(**kwargs):
        frame = eastmoney_frame()
        frame['成交额'] = 10000  # Raw average = 1 yuan per share.
        if kwargs['adjust'] == '':
            frame['收盘'] = 1.0
        return frame

    monkeypatch.setattr(data_service.ak, 'fund_etf_hist_em', history)
    result = get_analysis_data('512710')
    assert result['close'][-1] == 0.5
    assert result['vwap'][-1] == 0.5
    assert result['maw243'][-1] == 0.5
