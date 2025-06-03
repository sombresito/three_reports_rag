import matplotlib.pyplot as plt
import os
from datetime import datetime

def plot_trends(reports, team_name):
    """График тренда passed/failed по последним 3 отчетам."""
    x = []
    passed = []
    failed = []
    for rep in reports:
        dt = rep.get("time", {}).get("start")
        if dt:
            x.append(datetime.fromtimestamp(dt/1000).strftime("%d-%m-%Y"))
        else:
            x.append("unknown")
        stat = {"passed": 0, "failed": 0}
        for suite in rep.get("children", []):
            for case in suite.get("children", []):
                status = case.get("status")
                if status in stat:
                    stat[status] += 1
        passed.append(stat["passed"])
        failed.append(stat["failed"])
    plt.figure(figsize=(6, 4))
    plt.plot(x, passed, marker='o', label='Passed')
    plt.plot(x, failed, marker='x', label='Failed')
    plt.title(f"Trends for {team_name}")
    plt.xlabel("Report Date")
    plt.ylabel("Tests")
    plt.legend()
    img_path = os.path.join("plots", f"trend_{team_name}.png")
    os.makedirs("plots", exist_ok=True)
    plt.savefig(img_path)
    plt.close()
    return img_path
