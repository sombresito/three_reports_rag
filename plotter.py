import matplotlib.pyplot as plt
from datetime import datetime
import os
import re
from collections import Counter, defaultdict

def safe_filename(name):
    """
    Делает имя файла безопасным для Windows и Linux:
    - Только латиница, цифры, подчеркивание
    - Ограничение длины (до 40 символов)
    """
    name = name.encode("ascii", "ignore").decode("ascii")
    name = re.sub(r'\W+', '_', name)
    return name[:40]

def plot_trends(cases, team_name):
    """
    Строит график тренда passed/failed/skipped по датам.
    cases: список тест-кейсов (dict)
    team_name: имя команды (будет в названии файла)
    """
    # Сбор дат и статусов
    dates = []
    statuses = []
    for case in cases:
        t = case.get("time", {})
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

    # Оставляем только валидные даты
    filtered = [(d, s) for d, s in zip(dates, statuses) if d]
    if not filtered:
        print("[PLOT] Нет данных для построения тренда!")
        return None

    # Группируем по дню
    date_to_status = defaultdict(list)
    for d, s in filtered:
        day = d.date()
        date_to_status[day].append(s)

    trend = {}
    for day, statlist in date_to_status.items():
        cnt = Counter(statlist)
        trend[day] = {
            "passed": cnt.get("passed", 0),
            "failed": cnt.get("failed", 0),
            "skipped": cnt.get("skipped", 0),
        }

    days = sorted(trend.keys())
    passed = [trend[d]["passed"] for d in days]
    failed = [trend[d]["failed"] for d in days]
    skipped = [trend[d]["skipped"] for d in days]

    # Готовим папку и путь к файлу
    plot_name = safe_filename(team_name)
    os.makedirs("plots", exist_ok=True)
    img_path = f"plots/trend_{plot_name}.png"

    # Строим график
    plt.figure(figsize=(8, 4))
    plt.plot(days, passed, label="Passed", marker='o')
    plt.plot(days, failed, label="Failed", marker='o')
    plt.plot(days, skipped, label="Skipped", marker='o')
    plt.xlabel("Date")
    plt.ylabel("Count")
    plt.title(f"Trend for {team_name}")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(img_path)
    plt.close()
    print(f"[PLOT] Saved trend plot: {img_path}")
    return img_path
