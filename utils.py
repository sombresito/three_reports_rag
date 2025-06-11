import os
from dotenv import load_dotenv
import requests

load_dotenv()

def get_env(key, default=None):
    return os.getenv(key, default)

def save_analysis_result(uuid, analysis):
    os.makedirs("analysis", exist_ok=True)
    path = f"analysis/{uuid}.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(analysis))

def send_analysis_to_allure(uuid, analysis):
    import requests
    from requests.auth import HTTPBasicAuth
    allure_api = f"{get_env('ALLURE_API_ANALYSIS_ENDPOINT')}/{uuid}"
    user = get_env('ALLURE_API_USER')
    pwd = get_env('ALLURE_API_PASSWORD')
    resp = requests.post(allure_api, json=analysis, auth=HTTPBasicAuth(user, pwd))
    if resp.status_code != 200:
        raise Exception(f"Failed to send analysis: {resp.text}")

def analyze_cases_with_llm(all_reports, team_name, trend_text=None, trend_img_path=None):
    """Invoke LLM to analyse provided test cases.

    Parameters
    ----------
    all_reports : list
        List of test case lists (current + previous reports).
    team_name : str
        Name of the team.
    trend_text : str, optional
        Textual representation of trends for the LLM.
    trend_img_path : str, optional
        Path to the trend image created by :mod:`plotter`. The image is
        returned as an Allure attachment but is not included in the LLM
        prompt.
    """

    from collections import Counter, defaultdict
    from datetime import datetime
    from plotter import flatten_report

    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    llm_model = os.getenv("LLM_MODEL", "gemma3:4b")

    # "all_reports" may contain nested lists, flatten them
    cases = []
    for rep in all_reports:
        cases.extend(flatten_report(rep))

    # --- Run periods & environment/initiators info ---
    starts, stops = [], []
    env_info = defaultdict(set)
    initiators = set()
    for c in cases:
        t = c.get("time") or {}
        if isinstance(t.get("start"), (int, float)):
            starts.append(t["start"])
        if isinstance(t.get("stop"), (int, float)):
            stops.append(t["stop"])
        for lbl in c.get("labels", []):
            name = lbl.get("name")
            val = lbl.get("value")
            if not name or val is None:
                continue
            if name in {"host", "thread", "framework", "language", "browser", "os", "env"}:
                env_info[name].add(val)
            if name in {"owner", "user", "initiator"}:
                initiators.add(val)

    run_period = "неизвестно"
    if starts and stops:
        start_ts = min(starts)
        stop_ts = max(stops)
        if start_ts > 1e10:
            start_ts /= 1000.0
        if stop_ts > 1e10:
            stop_ts /= 1000.0
        start = datetime.fromtimestamp(start_ts).isoformat()
        stop = datetime.fromtimestamp(stop_ts).isoformat()
        run_period = f"{start} – {stop}"

    env_str = ", ".join(f"{k}:{','.join(sorted(v))}" for k, v in env_info.items()) or "неизвестно"
    initiators_str = ", ".join(sorted(initiators)) or "неизвестно"

    # --- Status distribution ---
    status_counts = Counter((c.get("status") or "unknown").lower() for c in cases)
    total = sum(status_counts.values()) or 1
    status_parts = [
        f"{s}={cnt} ({cnt * 100 / total:.1f}%)" for s, cnt in status_counts.items()
    ]
    status_summary = "; ".join(status_parts)

    # --- Problematic areas ---
    error_clusters = Counter()
    locator_failures = 0
    flaky_count = 0
    for c in cases:
        if c.get("flaky"):
            flaky_count += 1
        status = (c.get("status") or "").lower()
        if status in {"failed", "broken"}:
            msg = c.get("statusMessage") or ""
            trace = c.get("statusTrace") or ""
            key = (msg.splitlines()[0] if msg else trace.splitlines()[0])[:120]
            if key:
                error_clusters[key] += 1
            if "no such element" in trace.lower() or "nosuchelement" in trace.lower() or "element not found" in msg.lower():
                locator_failures += 1

    top_errors = "; ".join(
        f"{m} x{c}" for m, c in error_clusters.most_common(3)
    ) or "нет"

    # --- Optimisation hints ---
    name_counter = Counter(c.get("name") for c in cases if c.get("name"))
    duplicates = [n for n, c in name_counter.items() if c > 1]
    duplicates_info = ", ".join(duplicates) if duplicates else "нет"

    step_counter = Counter()

    def _collect_steps(steps):
        if not steps:
            return
        for st in steps:
            if st.get("name"):
                step_counter[st["name"]] += 1
            _collect_steps(st.get("steps"))

    for c in cases:
        _collect_steps(c.get("steps"))

    common_steps = ", ".join(
        f"{n} x{c}" for n, c in step_counter.most_common(3)
    ) if step_counter else "нет"

    # --- Mandatory fields validation ---
    mandatory_fields = [
        "name",
        "status",
        "uid",
        "description",
        "owner",
        "labels",
        "jira",
    ]
    missing = []
    for c in cases:
        miss = [f for f in mandatory_fields if not c.get(f)]
        if miss:
            missing.append(f"{c.get('uid', '?')}: {', '.join(miss)}")
    missing_summary = "; ".join(missing) if missing else "нет"

    # --- Form prompt for LLM ---
    text = (
        f"Команда: {team_name}\n"
        f"Период запуска: {run_period}\n"
        f"Окружение: {env_str}\n"
        f"Инициаторы: {initiators_str}\n\n"
        f"Статусы: {status_summary}\n"
        f"Ошибки: {top_errors}\n"
        f"Не найдено локаторов: {locator_failures}\n"
        f"Флейки: {flaky_count}\n"
        f"Дубли тестов: {duplicates_info}\n"
        f"Повторяющиеся шаги: {common_steps}\n"
        f"Обязательные поля (name, status, uid, description, owner, labels, jira): {missing_summary}\n"
    )

    if trend_text:
        text += f"\nТренд по датам:\n{trend_text}\n"

    text += ("\nСделай вывод о стабильности тестов, ключевых проблемах и дай краткие рекомендации."
             " Ответ дай на русском, по существу.")

    payload = {
        "model": llm_model,
        "prompt": text,
        "stream": False,
    }
    llm_ok = True
    try:
        response = requests.post(ollama_url, json=payload)
        response.raise_for_status()
        result = response.json()
        summary = result.get("response", "").strip() or result.get("message", "Нет ответа от LLM")
    except Exception as e:
        llm_ok = False
        summary = f"Ошибка вызова LLM: {e}"

    rules = [
        ("auto-analysis", summary)
    ]

    return summary, rules


