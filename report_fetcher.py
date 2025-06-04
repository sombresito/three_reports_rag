import requests
from requests.auth import HTTPBasicAuth
from utils import get_env

def fetch_allure_report(uuid: str) -> dict:
    url = f"{get_env('ALLURE_API_REPORT_ENDPOINT')}/{uuid}/test-cases/aggregate"
    print("[FETCH]", url)
    user = get_env('ALLURE_API_USER')
    pwd = get_env('ALLURE_API_PASSWORD')
    resp = requests.get(url, auth=HTTPBasicAuth(user, pwd))
    print("[FETCH STATUS]", resp.status_code)
    print("[FETCH TEXT]", resp.text[:500])
    if resp.status_code != 200:
        raise Exception(f"Allure report {uuid} not found, status: {resp.status_code}")
    return resp.json()
