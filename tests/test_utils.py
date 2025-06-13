import io
import os
import sys
import types
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

sys.modules.setdefault("dotenv", types.SimpleNamespace(load_dotenv=lambda: None))
requests_stub = types.SimpleNamespace(post=lambda *a, **k: None)
class HTTPBasicAuth:
    def __init__(self, user, pwd):
        self.user = user
        self.pwd = pwd
requests_stub.auth = types.SimpleNamespace(HTTPBasicAuth=HTTPBasicAuth)
sys.modules.setdefault("requests", requests_stub)
sys.modules.setdefault("requests.auth", requests_stub.auth)
sys.modules.setdefault("numpy", types.SimpleNamespace())
sys.modules.setdefault("matplotlib", types.SimpleNamespace(pyplot=types.SimpleNamespace()))
sys.modules.setdefault("matplotlib.pyplot", types.SimpleNamespace())
sys.modules.setdefault("qdrant_client", types.SimpleNamespace(QdrantClient=object))
sys.modules.setdefault(
    "qdrant_client.models", types.SimpleNamespace(PointStruct=object, Distance=object, VectorParams=object)
)
import utils


def test_analyze_cases_returns_img_path(monkeypatch, tmp_path):
    img = tmp_path / "trend.png"
    img.write_bytes(b"123")

    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"response": "summary"}

    monkeypatch.setattr(utils.requests, "post", lambda *a, **k: Resp())
    summary, rules, path = utils.analyze_cases_with_llm(
        [[{"status": "passed", "uid": "1", "name": "t"}]],
        "team",
        trend_text="t",
        trend_img_path=str(img),
    )
    assert path == str(img)
    assert summary
    assert rules == [("auto-analysis", summary)]


def test_send_analysis_with_files(monkeypatch, tmp_path):
    captured = {}

    def fake_post(url, **kwargs):
        captured.update(kwargs)

        class R:
            status_code = 200
            text = "ok"

        return R()

    monkeypatch.setenv("ALLURE_API_ANALYSIS_ENDPOINT", "http://x")
    monkeypatch.setenv("ALLURE_API_USER", "u")
    monkeypatch.setenv("ALLURE_API_PASSWORD", "p")
    monkeypatch.setenv("ALLURE_ALLOW_ATTACHMENTS", "false")
    monkeypatch.setattr(utils.requests, "post", fake_post)

    path = tmp_path / "trend.png"
    path.write_bytes(b"img")
    with open(path, "rb") as f:
        analysis = [{"rule": "trend-image", "attachment": f}]
        utils.send_analysis_to_allure("uid", analysis, files={"trend-image": f})

    assert "json" in captured
    assert captured["json"] == analysis
