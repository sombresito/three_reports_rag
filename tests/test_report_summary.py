import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from report_summary import _format_date


def test_format_date_valid():
    ts_values = [1700000000, 170000000]
    for ts in ts_values:
        expected = datetime.fromtimestamp(ts).strftime('%d.%m.%Y (%H:%M)')
        assert _format_date(ts) == expected

