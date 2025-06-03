import requests
from requests.auth import HTTPBasicAuth
from utils import get_env

def fetch_allure_report(uuid: str) -> dict:
    url = f"{get_env('ALLURE_API_REPORT_ENDPOINT')}/{uuid}/suites/json"
    user = get_env('ALLURE_API_USER')
    pwd = get_env('ALLURE_API_PASSWORD')
    resp = requests.get(url, auth=HTTPBasicAuth(user, pwd))
    if resp.status_code != 200:
        raise Exception(f"Allure report {uuid} not found, status: {resp.status_code}")
    return resp.json()
