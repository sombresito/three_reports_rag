import os
from dotenv import load_dotenv

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
    allure_api = f"{get_env('ALLURE_HOST')}/api/analysis/report/{uuid}"
    resp = requests.post(allure_api, json=analysis)
    if resp.status_code != 200:
        raise Exception(f"Failed to send analysis: {resp.text}")
