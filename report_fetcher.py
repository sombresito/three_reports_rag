import requests
from requests.auth import HTTPBasicAuth
from utils import get_env

def _flatten_suites(node, cases):
    if isinstance(node, dict):
        if "children" in node:
            for child in node["children"]:
                _flatten_suites(child, cases)
        # Leaf test case nodes may have status/name/uid
        if (
            (node.get("type") == "testcase")
            or ("status" in node and "uid" in node and "name" in node and "children" not in node)
        ):
            cases.append(node)


def fetch_allure_report(uuid: str) -> list:
    base = get_env("ALLURE_API_REPORT_ENDPOINT")
    url = f"{base}/{uuid}/suites/json"
    print("[FETCH]", url)
    user = get_env('ALLURE_API_USER')
    pwd = get_env('ALLURE_API_PASSWORD')
    resp = requests.get(url, auth=HTTPBasicAuth(user, pwd))
    print("[FETCH STATUS]", resp.status_code)
    print("[FETCH TEXT]", resp.text[:500])
    if resp.status_code != 200:
        raise Exception(
            f"Allure report {uuid} not found, status: {resp.status_code}"
        )

    data = resp.json()

    # API /suites/json returns hierarchical suites. Convert to flat list of test cases
    cases = []
    if isinstance(data, dict):
        _flatten_suites(data, cases)
    elif isinstance(data, list):
        if data and all(isinstance(x, dict) and "children" in x for x in data):
            for item in data:
                _flatten_suites(item, cases)
        else:
            cases = data
    else:
        raise Exception("Unexpected Allure response format")

    return cases
