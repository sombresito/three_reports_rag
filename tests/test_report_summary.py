import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from report_summary import _format_date
from report_summary import format_reports_summary


def _sample_report(ts, team):
    return [
        {
            "name": "t1",
            "status": "passed",
            "time": {"start": ts},
            "labels": [{"name": "parentSuite", "value": team}],
        }
    ]


def test_format_date_valid():
    ts_values = [1700000000, 170000000]
    for ts in ts_values:
        expected = datetime.fromtimestamp(ts).strftime('%d.%m.%Y (%H:%M)')
        assert _format_date(ts) == expected


def test_format_reports_summary_team_name():
    ts = 1700000000
    report = _sample_report(ts, "alpha")
    summary = format_reports_summary([report], color=False, timestamps=[ts])
    lines = summary.splitlines()
    assert lines[1] == "Команда: alpha"

