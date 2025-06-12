from datetime import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import report_summary


def test_format_date_valid():
    ts = 1700000000
    expected = datetime.fromtimestamp(ts).strftime('%d.%m.%Y (%H:%M)')
    assert report_summary._format_date(ts) == expected
