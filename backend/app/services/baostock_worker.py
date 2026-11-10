"""One isolated BaoStock session; stdout contains only the resulting frame."""
from contextlib import redirect_stdout
from datetime import date
import sys

from app.services.minute_data_service import (
    _download_baostock_direct, _normalize_period, normalize_minute_code,
)


def main() -> None:
    code, period, start, end = sys.argv[1:]
    # BaoStock prints login/logout messages, which must not corrupt JSON output.
    with redirect_stdout(sys.stderr):
        frame = _download_baostock_direct(
            normalize_minute_code(code), _normalize_period(period),
            date.fromisoformat(start), date.fromisoformat(end),
        )
    print(frame.to_json(orient='split', force_ascii=True))


if __name__ == '__main__':
    main()
