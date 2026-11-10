import json
import subprocess
import sys
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from app.services import minute_data_service as service


def test_baostock_timeout_terminates_hung_child(monkeypatch):
    # Exercise a real hung child, without relying on the external data source.
    real_run = subprocess.run

    def hung_provider(command, **kwargs):
        assert 0 < kwargs['timeout'] < 180
        kwargs['timeout'] = 0.1
        return real_run([sys.executable, '-c', 'import time; time.sleep(60)'], **kwargs)

    monkeypatch.setattr(subprocess, 'run', hung_provider)
    monkeypatch.setattr(service.bs, 'login', lambda: SimpleNamespace(
        error_code='1', error_msg='In-process provider must not be used',
    ))
    with pytest.raises(TimeoutError, match='BaoStock'):
        service._download_baostock('002156', '30', date(2024, 10, 20), date(2026, 10, 20))


def test_baostock_worker_result_preserves_code_and_period(monkeypatch):
    frame = service.normalize_baostock_minutes([[
        '2026-10-20', '20261020150000000', 'sz.002156',
        '40', '42', '39', '41', '1000', '41000', '2',
    ]], '002156', '30')
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(
        returncode=0, stdout=frame.to_json(orient='split'), stderr='',
    ))
    monkeypatch.setattr(service.bs, 'login', lambda: SimpleNamespace(
        error_code='1', error_msg='In-process provider must not be used',
    ))
    result = service._download_baostock(
        '002156', '30', date(2024, 10, 20), date(2026, 10, 20),
    )
    assert result['股票代码'].tolist() == ['002156']
    assert result['周期'].tolist() == ['30']
    assert result['收盘'].tolist() == [41.0]


def test_worker_keeps_provider_logs_out_of_json(monkeypatch, capsys):
    from app.services import baostock_worker

    def download(code, period, start, end):
        assert (code, period, start, end) == (
            '002156', '30', date(2024, 10, 20), date(2026, 10, 20),
        )
        print('login success!')
        return pd.DataFrame({'股票代码': ['002156'], '周期': ['30'], '收盘': [41.0]})

    monkeypatch.setattr(baostock_worker, '_download_baostock_direct', download)
    monkeypatch.setattr(sys, 'argv', [
        'baostock_worker', '002156', '30', '2024-10-20', '2026-10-20',
    ])
    baostock_worker.main()
    captured = capsys.readouterr()
    assert json.loads(captured.out)['data'] == [['002156', '30', 41.0]]
    assert 'login success!' in captured.err


def test_baostock_worker_failure_uses_existing_fallback(monkeypatch):
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(
        returncode=1, stdout='', stderr='provider unavailable',
    ))
    monkeypatch.setattr(service.bs, 'login', lambda: SimpleNamespace(
        error_code='1', error_msg='provider unavailable',
    ))
    fallback = pd.DataFrame({
        'day': ['2026-10-20 15:00:00'], 'open': [40.0], 'high': [42.0],
        'low': [39.0], 'close': [41.0], 'volume': [1000], 'amount': [41000],
    })
    monkeypatch.setattr(service, '_download_akshare', lambda *args: (fallback, 'akshare_sina'))
    result, metadata = service.download_minute_data('002156', '30')
    assert metadata['data_source'] == 'akshare_sina'
    assert result['股票代码'].tolist() == ['002156']
