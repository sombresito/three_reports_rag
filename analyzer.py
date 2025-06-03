import requests
import os
from utils import get_env

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma3:4b")

def analyze_reports(report, prev_reports, plot_img_path):
    # Формируем промпт для LLM
    prompt = (
        "Ты — эксперт по автотестам. Проведи глубокий анализ текущего отчёта и сравни с предыдущими. "
        f"Кратко: в чем основные тренды, какие ошибки повторяются, есть ли улучшения или деградация? "
        "Выполни также статистический и визуальный анализ на основе приложенного графика по пути: "
        f"{plot_img_path}.\n\n"
        "Данные текущего отчёта:\n"
        f"{report}\n\n"
        "Данные прошлых отчётов:\n"
        f"{prev_reports}"
    )
    data = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False
    }
    resp = requests.post(OLLAMA_URL, json=data)
    if resp.status_code != 200:
        raise Exception(f"LLM error: {resp.text}")
    output = resp.json()["response"]
    # Возвращаем в правильном формате
    return [
        {
            "rule": "auto-analysis",
            "message": output
        }
    ]
