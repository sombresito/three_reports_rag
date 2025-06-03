import requests
from utils import get_env

def fetch_allure_report(uuid: str) -> dict:
    url = f"{get_env('ALLURE_HOST')}/api/report/{uuid}/suites/json"
    resp = requests.get(url)
    if resp.status_code != 200:
        raise Exception(f"Allure report {uuid} not found")
    return resp.json()
