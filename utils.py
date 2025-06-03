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

def analyze_cases_with_llm(all_cases, team_name, trend_text=None):
    ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
    llm_model = os.getenv("LLM_MODEL", "gemma3:4b")

    text = f"Тестовые кейсы команды {team_name}:\n"
    for i, case in enumerate(all_cases[:20]):  # Можно больше/меньше
        text += f"{i+1}. {case.get('name', 'без имени')} - статус: {case.get('status', '')}\n"
    if trend_text:
        text += f"\nДинамика тестов по датам:\n{trend_text}\n"
    text += "\nСделай краткое резюме по стабильности тестов, выдели проблемные зоны и дай 2-3 рекомендации. Ответ дай на русском, коротко и по делу."

    payload = {
        "model": llm_model,
        "prompt": text,
        "stream": False
    }
    try:
        response = requests.post(ollama_url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        summary = result.get("response", "").strip() or result.get("message", "Нет ответа от LLM")
    except Exception as e:
        summary = f"Ошибка вызова LLM: {e}"

    rules = [
        ("auto-analysis", summary)
    ]
    return summary, rules


