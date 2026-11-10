import asyncio
from threading import Event

import httpx
import pytest

from app.main import app


@pytest.mark.parametrize(
    ('path', 'payload', 'service'),
    [
        ('/api/analysis/run', {'stock_code': '002156'}, 'analysis.get_analysis_data'),
        ('/api/data/refresh', {'stock_code': '002156'}, 'data.refresh_stock_data'),
        ('/api/backtest/run', {
            'stock_code': '002156', 'start_date': '2026-01-01',
            'end_date': '2026-10-20',
        }, 'backtest.run_backtest'),
        ('/api/chan/analyze', {'stock_code': '002156', 'period': '30'}, 'chan.analyze_chan'),
        ('/api/chan/refresh', {'stock_code': '002156', 'period': '30'}, 'chan.refresh_minute_data'),
        ('/api/fund/analysis', {'fund_code': '000001'}, 'fund.get_fund_analysis'),
        ('/api/fund/refresh', {'fund_code': '000001'}, 'fund.refresh_fund'),
        ('/api/fund/backtest', {
            'fund_code': '000001', 'strategy_name': 'weekly_investment',
            'start_date': '2026-01-01', 'weekday': 5, 'amount': 1000,
        }, 'fund.run_fund_backtest'),
    ],
)
def test_slow_service_does_not_block_other_requests(monkeypatch, path, payload, service):
    started, release, finished = Event(), Event(), Event()

    def slow_service(*args, **kwargs):
        started.set()
        try:
            # Finite watchdog makes the broken event-loop implementation fail, not hang.
            release.wait(2)
            return {'success': True}
        finally:
            finished.set()

    monkeypatch.setattr(f'app.api.{service}', slow_service)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url='http://test',
        ) as client:
            pending = asyncio.create_task(client.post(path, json=payload))
            try:
                assert await asyncio.to_thread(started.wait, 3)
                health = await client.get('/health')
                assert health.json() == {'status': 'ok'}
                assert not finished.is_set(), 'Slow service blocked the event loop'
            finally:
                release.set()
                response = await pending
            assert response.status_code == 200
            assert response.json() == {'success': True}

    asyncio.run(scenario())
