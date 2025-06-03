import matplotlib.pyplot as plt
from datetime import datetime

def plot_trends(cases, team_name):
    # Соберём данные по датам запусков и статусам
    dates = []
    statuses = []

    for case in cases:
        # Предполагаем что case — dict
        t = case.get("time", {})
        # В Allure "start" может быть timestamp или строка; преобразуем к datetime
        dt = t.get("start")
        if isinstance(dt, (int, float)):
            dt = datetime.fromtimestamp(dt / 1000)
        elif isinstance(dt, str):
            try:
                dt = datetime.fromisoformat(dt)
            except Exception:
                dt = None
        statuses.append(case.get("status", "unknown"))
        dates.append(dt)

    # Фильтруем невалидные даты
    filtered = [(d, s) for d, s in zip(dates, statuses) if d]
    if not filtered:
        print("[PLOT] Нет данных для построения тренда!")
        return None

    # Группируем по дате (можно по дням, часам — зависит от granularity)
    from collections import Counter, defaultdict
    date_to_status = defaultdict(list)
    for d, s in filtered:
        day = d.date()
        date_to_status[day].append(s)

    # Строим тренд по passed/failed/skipped
    trend = {}
    for day, statlist in date_to_status.items():
        cnt = Counter(statlist)
        trend[day] = {
            "passed": cnt.get("passed", 0),
            "failed": cnt.get("failed", 0),
            "skipped": cnt.get("skipped", 0),
        }

    # Готовим данные для графика
    days = sorted(trend.keys())
    passed = [trend[d]["passed"] for d in days]
    failed = [trend[d]["failed"] for d in days]
    skipped = [trend[d]["skipped"] for d in days]

    plt.figure(figsize=(8, 4))
    plt.plot(days, passed, label="Passed", marker='o')
    plt.plot(days, failed, label="Failed", marker='o')
    plt.plot(days, skipped, label="Skipped", marker='o')
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.title(f"Trend for {team_name}")
    plt.legend()
    plt.grid(True)
    img_path = f"plots/trend_{team_name}.png"
    plt.tight_layout()
    plt.savefig(img_path)
    plt.close()
    print(f"[PLOT] Saved trend plot: {img_path}")
    return img_path
