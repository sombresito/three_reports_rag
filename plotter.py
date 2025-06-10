import os
import matplotlib.pyplot as plt
from collections import defaultdict
import numpy as np

PLOT_DIR = "plots"
MAX_TRENDS = 3

COLORS = {
    "passed": "green",
    "failed": "red",
    "broken": "orange",
    "skipped": "gray"
}

def ensure_plot_dir():
    os.makedirs(PLOT_DIR, exist_ok=True)

def flatten_report(report):
    # Если report — список списков, развернём
    if report and isinstance(report[0], list):
        result = []
        for sublist in report:
            result.extend(sublist)
        return result
    return report

def plot_individual_bar(report, uuid):
    ensure_plot_dir()
    report = flatten_report(report)
    statuses = ["passed", "failed", "broken", "skipped"]
    counts = {k: 0 for k in statuses}
    for test in report:
        status = (test.get("status") or "").lower()
        if status in counts:
            counts[status] += 1
    plt.figure(figsize=(6, 4))
    plt.bar(
        statuses,
        [counts[s] for s in statuses],
        color=[COLORS[s] for s in statuses]
    )
    plt.title(f"Статусы тестов (отчёт: {uuid[:8]})")
    plt.ylabel("Количество тестов")
    plt.xlabel("")
    plt.tight_layout()
    fname = f"{PLOT_DIR}/trend_{uuid}.png"
    plt.savefig(fname)
    plt.close()
    return fname

def get_existing_trend_uuids():
    ensure_plot_dir()
    files = [f for f in os.listdir(PLOT_DIR) if f.startswith("trend_") and f.endswith(".png") and not f.endswith("summary.png")]
    uuids = []
    for f in files:
        if f.startswith("trend_") and f.endswith(".png"):
            parts = f[len("trend_"):-len(".png")]
            uuids.append(parts)
    return uuids

def remove_old_trend_charts(latest_uuids):
    """Удаляет bar-графики старых uuid, если их больше MAX_TRENDS"""
    ensure_plot_dir()
    all_uuids = get_existing_trend_uuids()
    for uuid in all_uuids:
        if uuid not in latest_uuids:
            path = os.path.join(PLOT_DIR, f"trend_{uuid}.png")
            if os.path.exists(path):
                os.remove(path)

def plot_summary_trend(reports, uuids, team_names):
    ensure_plot_dir()
    statuses = ["passed", "failed", "broken", "skipped"]
    trend = {s: [] for s in statuses}
    labels = []
    for i, report in enumerate(reports):
        report = flatten_report(report)
        counts = {s: 0 for s in statuses}
        for t in report:
            status = (t.get("status") or "").lower()
            if status in counts:
                counts[status] += 1
        for s in statuses:
            trend[s].append(counts[s])
        labels.append((team_names[i] or uuids[i][:8]))

    x = np.arange(1, len(reports) + 1)
    plt.figure(figsize=(10, 5))
    for s in statuses:
        plt.plot(x, trend[s], marker="o", color=COLORS[s], label=s.capitalize(), linewidth=2)
    plt.title("Тренд последних 3 отчётов (по порядку)")
    plt.xlabel("Очередность")
    plt.ylabel("Количество тестов")
    plt.xticks(x, labels, rotation=30, ha='right')
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    fname = f"{PLOT_DIR}/trend_summary.png"
    plt.savefig(fname)
    plt.close()
    return fname

def plot_trends_for_reports(reports, uuids, team_names):
    """
    reports: list of test-cases (по каждому отчёту, max 3)
    uuids:   list of uuids (по каждому отчёту, max 3)
    team_names: list of команд (по каждому отчёту, max 3)
    """
    ensure_plot_dir()
    # 1. Бар-графики для каждого отчёта
    for i, (report, uuid) in enumerate(zip(reports, uuids)):
        plot_individual_bar(report, uuid)
    # 2. Сохраняем только 3 последних bar-чарта
    remove_old_trend_charts(set(uuids))
    # 3. Summary trend
    return plot_summary_trend(reports, uuids, team_names)
