"""Utilities to summarise Allure reports."""

from collections import Counter
from typing import List, Dict, Any, Optional
from datetime import datetime


STATUS_ORDER = ["passed", "failed", "broken", "skipped"]
ANSI_COLORS = {
    "passed": "\033[32m",
    "failed": "\033[31m",
    "broken": "\033[33m",
    "skipped": "\033[90m",
    "reset": "\033[0m",
}

# HTML color mapping used when ``color=True`` is requested by
# :func:`format_reports_summary`.  React does not understand ANSI
# escape codes, so we output ``<span>`` tags instead.
HTML_COLORS = {
    "passed": "green",
    "failed": "red",
    "broken": "orange",
    "skipped": "gray",
}


def _format_date(ts: int) -> str:
    """Return ``dd.mm.yyyy (HH:MM)`` formatted date for ``ts`` seconds since epoch."""
    if ts <= 0:
        ts = 0
    return datetime.fromtimestamp(ts).strftime("%d.%m.%Y (%H:%M)")


def _normalize_timestamp(ts: float) -> int:
    """Return unix timestamp in seconds for ``ts`` which may be in ms."""
    if ts > 1e10:
        ts /= 1000.0
    return int(ts)


def extract_report_info(report: List[Dict[str, Any]], fallback_timestamp: int = 0) -> Dict[str, Any]:
    """Extract key fields from an Allure report.

    Parameters
    ----------
    report : list
        Flat list of test case dictionaries.

    fallback_timestamp : int, optional
        Timestamp to use if cases do not contain timing information.

    Returns
    -------
    dict with keys ``timestamp``, ``team_name``, ``status_counts``, ``initiators``,
    ``jira_links`` and ``duplicates``.
    """
    earliest = None
    team_names = set()
    status_counts = Counter()
    initiators = set()
    jira_links = set()
    name_counter = Counter()

    for case in report:
        t = case.get("time") or {}
        start = t.get("start")
        ts_fallback = case.get("timestamp")
        if isinstance(start, (int, float)):
            if earliest is None or start < earliest:
                earliest = start
        elif isinstance(ts_fallback, (int, float)):
            if earliest is None or ts_fallback < earliest:
                earliest = ts_fallback

        for lbl in case.get("labels", []):
            name = lbl.get("name")
            val = lbl.get("value")
            if not name or val is None:
                continue
            if name == "parentSuite":
                team_names.add(val)
            if name in {"owner", "user", "initiator"}:
                initiators.add(val)

        status = (case.get("status") or "").lower()
        if status in STATUS_ORDER:
            status_counts[status] += 1

        for link in case.get("links", []):
            if not isinstance(link, dict):
                continue
            type_name = str(link.get("type") or link.get("name") or "").lower()
            if "jira" in type_name:
                url = link.get("url")
                if url:
                    jira_links.add(url)
        jira_field = case.get("jira")
        if isinstance(jira_field, str):
            jira_links.add(jira_field)
        elif isinstance(jira_field, list):
            for j in jira_field:
                if isinstance(j, str):
                    jira_links.add(j)
                elif isinstance(j, dict):
                    url = j.get("url") or j.get("id") or j.get("name")
                    if url:
                        jira_links.add(str(url))

        name = case.get("name")
        if name:
            name_counter[name] += 1

    duplicates = [n for n, c in name_counter.items() if c > 1]

    if earliest is None:
        earliest = fallback_timestamp
    timestamp = _normalize_timestamp(earliest)
    if len(team_names) == 1:
        team_name = next(iter(team_names))
    elif team_names:
        team_name = "_".join(sorted(team_names))
    else:
        team_name = ""

    info = {
        "timestamp": timestamp,
        "team_name": team_name,
        "status_counts": {s: status_counts.get(s, 0) for s in STATUS_ORDER},
        "initiators": sorted(initiators),
        "jira_links": sorted(jira_links),
        "duplicates": sorted(duplicates),
    }
    return info


def _fmt_status(s: str, cnt: int, color: bool) -> str:
    if color:
        html_color = HTML_COLORS.get(s)
        if html_color:
            return f"<span style=\"color: {html_color};\">{s}={cnt}</span>"
        return f"{s}={cnt}"
    return f"{s}={cnt}"


def format_reports_summary(
    reports: List[List[Dict[str, Any]]],
    color: bool = True,
    timestamps: Optional[List[int]] = None,
) -> str:
    """Return human readable summary for multiple reports."""
    infos = []
    for idx, r in enumerate(reports):
        ts = timestamps[idx] if timestamps and idx < len(timestamps) else 0
        infos.append(extract_report_info(r, fallback_timestamp=ts))
    lines = []
    for info in infos:
        ts = info["timestamp"]
        date_str = _format_date(ts)
        sc = info["status_counts"]
        status_line = ", ".join(_fmt_status(s, sc.get(s, 0), color) for s in STATUS_ORDER)
        lines.append(f"**{date_str}**: {status_line}")
        if info["team_name"]:
            lines.append(f"**Команда**: {info['team_name']}")
        initiators = ", ".join(info["initiators"]) if info["initiators"] else "нет"
        lines.append(f"**Инициаторы**: {initiators}")
        for link in info["jira_links"]:
            lines.append(f"**jira**: {link}")
        if info["duplicates"]:
            dups = ", ".join(info["duplicates"])
            lines.append(f"**Дубликаты в отчете {date_str}**: {dups}")
        else:
            lines.append(f"**Дубликаты в отчете {date_str}**: нет")
    return "\n".join(lines)

