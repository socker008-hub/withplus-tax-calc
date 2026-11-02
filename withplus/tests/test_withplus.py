"""위드플러스 래퍼 테스트 — 원본 엔진 테스트(상위 tests/)와 별도로 돈다.

실행(withplus 폴더에서):  uv run --extra test pytest -q
"""
import json

import pytest
from starlette.testclient import TestClient

from withplus_tax.config import Settings, parse_tokens
from withplus_tax.server import build_http_app

TOKEN = "test-token-abcdefghijklmnopqrstuvwxyz"
HOST = "mcp.withplustax.com"
HDR = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json", "Host": HOST}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    logs = tmp_path_factory.mktemp("logs")
    s = Settings(mode="public", public_hosts=[HOST], tokens={TOKEN: "조덕희"}, log_dir=logs)
    with TestClient(build_http_app(s), base_url=f"https://{HOST}") as c:
        c.logs = logs
        yield c


def rpc(client, method, params=None, *, token=TOKEN, headers=None, url="/mcp"):
    h = dict(HDR, **(headers or {}))
    if token:
        h["Authorization"] = f"Bearer {token}"
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post(url, headers=h, content=json.dumps(body))


def init(client, **kw):
    return rpc(client, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                      "clientInfo": {"name": "pytest", "version": "0"}}, **kw)


def test_short_token_rejected():
    with pytest.raises(ValueError):
        parse_tokens("kim:short")
    assert parse_tokens(f"kim:{TOKEN}") == {TOKEN: "kim"}


def test_health_without_token(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_no_token_401(client):
    assert init(client, token=None).status_code == 401
    assert init(client, token="wrong-token-wrong-token-wrong").status_code == 401


def test_initialize_with_bearer(client):
    r = init(client)
    assert r.status_code == 200, r.text
    info = r.json()["result"]["serverInfo"]
    assert info["name"] == "withplus-tax-calc"


def test_query_key_also_works(client):
    assert init(client, token=None, url=f"/mcp?key={TOKEN}").status_code == 200


def test_unknown_host_rejected(client):
    assert init(client, headers={"Host": "evil.example.com"}).status_code == 421


def test_server_file_tools_removed(client):
    names = {t["name"] for t in rpc(client, "tools/list").json()["result"]["tools"]}
    assert "corporate_tax" in names and "find_tool" in names
    for t in ("extract_relations", "tunnelling_from_pdf", "return_precheck_pdf", "export_workbook"):
        assert t not in names
    assert len(names) == 89


@pytest.mark.parametrize("tool,args,key,expected", [
    ("corporate_tax", {"base": 500_000_000, "year": 2025}, "산출세액", 75_000_000),
    ("corporate_tax", {"base": 500_000_000, "year": 2026}, "산출세액", 80_000_000),
    ("retirement_income_tax", {"income": 100_000_000, "years_of_service": 15, "retire_year": 2026}, "퇴직소득세", 2_175_000),
    ("underreporting_penalty", {"additional_tax": 10_000_000, "fraud": False}, "가산세", 1_000_000),
    ("late_payment_penalty", {"unpaid_tax": 10_000_000, "due": "2026-06-01", "until": "2026-10-07"}, "가산세", 281_600),
])
def test_calc_and_footer(client, tool, args, key, expected):
    r = rpc(client, "tools/call", {"name": tool, "arguments": args})
    data = json.loads(r.json()["result"]["content"][0]["text"])
    assert data["결과"][key] == expected
    assert "위드플러스" in data["안내"]


def test_usage_log_has_no_values(client):
    rpc(client, "tools/call", {"name": "corporate_tax", "arguments": {"base": 123_456_789, "year": 2025}})
    lines = [json.loads(x) for f in client.logs.glob("usage-*.jsonl") for x in f.read_text(encoding="utf-8").splitlines()]
    calls = [x for x in lines if x.get("tool") == "corporate_tax"]
    assert calls and calls[-1]["user"] == "조덕희" and calls[-1]["arg_keys"] == ["base", "year"]
    assert "123456789" not in "".join(f.read_text(encoding="utf-8") for f in client.logs.glob("*.jsonl"))
