import matplotlib.pyplot as plt
import os
import glob

MAX_TRENDS = 3  # Храним максимум 3 индивидуальных + 1 summary

def plot_trends_for_reports(reports_info):
    """
    reports_info: list of dicts, каждый dict {"uuid": ..., "passed": int, "failed": int, "broken": int, "skipped": int}
    """
    os.makedirs("plots", exist_ok=True)
    uuids = [r["uuid"] for r in reports_info]
    passed = [r.get("passed", 0) for r in reports_info]
    failed = [r.get("failed", 0) for r in reports_info]
    broken = [r.get("broken", 0) for r in reports_info]
    skipped = [r.get("skipped", 0) for r in reports_info]

    x = list(range(1, len(reports_info) + 1))
    labels = [f"{i+1}-й отчёт" for i in range(len(reports_info))]

    plt.figure(figsize=(9, 5))
    plt.plot(x, passed, '-o', label="Passed")
    plt.plot(x, failed, '-o', label="Failed")
    plt.plot(x, broken, '-o', label="Broken")
    plt.plot(x, skipped, '-o', label="Skipped")
    plt.xticks(x, labels)
    plt.xlabel("Очередность")
    plt.ylabel("Количество тестов")
    plt.title("Тренд по последним 3 отчётам")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    img_path = os.path.join("plots", "trend_summary.png")
    plt.savefig(img_path)
    plt.close()
    print(f"[PLOT] Saved summary trend: {img_path}")

def plot_individual_trend(report_info):
    """
    report_info: dict {"uuid": ..., "passed": int, "failed": int, "broken": int, "skipped": int}
    """
    os.makedirs("plots", exist_ok=True)
    uuid = report_info["uuid"]
    counts = [report_info.get("passed", 0), report_info.get("failed", 0),
              report_info.get("broken", 0), report_info.get("skipped", 0)]
    labels = ["Passed", "Failed", "Broken", "Skipped"]

    plt.figure(figsize=(6, 4))
    plt.bar(labels, counts, color=['green', 'red', 'orange', 'gray'])
    plt.title(f"Тренд отчёта {uuid[:8]}")
    plt.ylabel("Количество тестов")
    plt.tight_layout()

    img_path = os.path.join("plots", f"trend_{uuid}.png")
    plt.savefig(img_path)
    plt.close()
    print(f"[PLOT] Saved individual trend: {img_path}")

def cleanup_old_trends():
    files = sorted(glob.glob("plots/trend_*.png"), key=os.path.getmtime)
    # Оставить только 3 последних + summary
    keep = set(files[-MAX_TRENDS:])
    for f in files:
        if f not in keep and "summary" not in f:
            try:
                os.remove(f)
                print(f"[PLOT] Removed old trend: {f}")
            except Exception:
                pass

def build_report_info(report):
    """
    report: list of test-case dicts
    Возвращает: {"uuid": ..., "passed": N, "failed": M, "broken": K, "skipped": L}
    """
    # Нужно, чтобы report был списком тест-кейсов
    status_map = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0}
    for case in report:
        s = (case.get("status") or "").lower()
        if s in status_map:
            status_map[s] += 1
    return {**status_map}

# --------- Использование в main.py ---------
# Пример вызова:
# Для summary:
#   plot_trends_for_reports([dict1, dict2, dict3])
# Для индивидуального:
#   plot_individual_trend(dict1)
# После генерации всех: cleanup_old_trends()
# -------------------------------------------
