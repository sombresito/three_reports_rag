import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from report_summary import _format_date


def test_format_date_positive():
    ts = 1700000000
    expected = datetime.fromtimestamp(ts).strftime('%d.%m.%Y')
    assert _format_date(ts) == expected


def test_format_date_non_positive():
    expected = datetime.fromtimestamp(0).strftime('%d.%m.%Y')
    assert _format_date(0) == expected
    assert _format_date(-123) == expected

