import logging
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth
from utils import get_env

logger = logging.getLogger(__name__)

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


def fetch_allure_report(uuid: str) -> tuple[list, int]:
    """Return Allure report cases and the fetch timestamp."""

    base = get_env("ALLURE_API_REPORT_ENDPOINT")
    # Report path may vary between Allure versions. Allow overriding via env.
    # By default we try the newer "/test-cases/aggregate" endpoint and fall back
    # to the older "/suites/json" path for compatibility.
    main_path = get_env("ALLURE_API_REPORT_PATH", "/test-cases/aggregate")
    paths = [main_path]
    if main_path != "/suites/json":
        paths.append("/suites/json")

    user = get_env("ALLURE_API_USER")
    pwd = get_env("ALLURE_API_PASSWORD")
    resp = None
    data = None
    for path in paths:
        path = "/" + path.lstrip("/")
        url = f"{base}/{uuid}{path}"
        logger.debug("[FETCH] %s", url)
        resp = requests.get(url, auth=HTTPBasicAuth(user, pwd))
        logger.debug("[FETCH STATUS] %s", resp.status_code)
        logger.debug("[FETCH TEXT] %s", resp.text[:500])
        if resp.status_code == 200:
            data = resp.json()
            break
    if resp is None or resp.status_code != 200:
        raise Exception(
            f"Allure report {uuid} not found, status: {resp.status_code}"
        )

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

    fetch_time = int(datetime.now().timestamp())
    return cases, fetch_time
