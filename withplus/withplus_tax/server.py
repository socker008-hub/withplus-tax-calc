"""세무법인 위드플러스 세금계산기 MCP 서버.

업스테이지 korean-tax-calc-mcp(MIT)의 계산 엔진을 그대로 불러와서, 원본 코드를 고치지 않고
위드플러스 운영에 필요한 것만 덧씌운다.

  - local 모드  : 내 PC의 Claude Desktop/Claude Code에서 쓰는 기본 모드(stdio). 원본과 동일 + 이름만 위드플러스.
  - public 모드 : withplustax.com 등 외부 공개용(HTTP). 아래 4가지를 추가한다.
      1) 접속 토큰 검사 — 토큰 없는 요청은 401 (세무사별 토큰 발급 가능)
      2) 서버 PC 파일 접근 도구 4개 끔 — PDF 경로 읽기·엑셀 파일 저장(외부인이 서버 PC 파일을 읽고 쓰는 것 차단)
      3) 공개 도메인 Host 허용 — 원본 HTTP 모드는 localhost 외 도메인 요청을 421로 거절함
      4) 사용 로그 — 누가 어떤 도구를 불렀는지만 기록(입력 금액·이름 등 값은 저장하지 않음)
      + 결과마다 '안내'(검토 보조자료·문의처) 문구 추가
"""
from __future__ import annotations

import argparse
import hmac
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs

from .config import SERVER_FILE_TOOLS, Settings, load_dotenv

KST = timezone(timedelta(hours=9))
SERVER_NAME = "withplus-tax-calc"
SERVER_TITLE = "위드플러스 세금계산기 (Withplus Tax Calculator)"
EXTRA_INSTRUCTIONS = (
    " 이 서버는 세무법인 위드플러스가 운영한다(엔진: Upstage korean-tax-calc-mcp, MIT). "
    "결과에 '안내' 항목이 있으면 답 끝에 그 문구를 함께 전한다. "
    "도구 결과는 검토 보조자료이며 사실관계 판단(요건 충족 여부 등)은 세무사 확인이 필요하다는 점을 답에 밝힌다."
)
MAX_BODY = 1_000_000  # 1MB — 계산 요청은 이보다 훨씬 작다

_configured = False


# ───────────────────────── MCP 서버 구성 ─────────────────────────

def build_server(settings: Settings):
    """원본 MCP 서버 객체에 위드플러스 설정을 적용해 돌려준다(원본 파일은 수정하지 않음)."""
    global _configured
    from korean_tax_calc_mcp.server import mcp  # 원본 엔진(93개 도구)

    if _configured:
        return mcp
    ll = mcp._lowlevel_server
    ll.name = SERVER_NAME
    ll.title = SERVER_TITLE
    ll.instructions = (ll.instructions or "") + EXTRA_INSTRUCTIONS

    if settings.mode == "public":
        existing = {t.name for t in mcp._tool_manager.list_tools()}
        for name in SERVER_FILE_TOOLS:
            if name in existing:
                mcp.remove_tool(name)
        if settings.footer:
            _install_footer(mcp, settings.footer)
    _configured = True
    return mcp


def _install_footer(mcp, footer: str) -> None:
    """외부 요청으로 들어온 도구 결과(JSON)에만 '안내' 항목을 붙인다.

    원본 export_workbook 등이 내부에서 call_tool을 다시 부를 때는 context가 없으므로 붙이지 않는다.
    """
    original = mcp.call_tool

    async def call_tool(name, arguments, context=None):
        result = await original(name, arguments, context)
        if context is None or getattr(result, "is_error", False):
            return result
        try:
            first = result.content[0]
            data = json.loads(first.text)
            if isinstance(data, dict) and "안내" not in data:
                data["안내"] = footer
                result.content[0] = first.model_copy(update={"text": json.dumps(data, ensure_ascii=False, indent=2)})
        except (AttributeError, IndexError, ValueError, TypeError):
            pass
        return result

    mcp.call_tool = call_tool


# ───────────────────────── 접속 토큰·로그 (ASGI) ─────────────────────────

class AccessGate:
    """토큰 검사 + 사용 로그. /health 는 토큰 없이 응답(가동 확인용)."""

    def __init__(self, app, settings: Settings):
        self.app = app
        self.tokens = settings.tokens
        self.log_dir = Path(settings.log_dir)

    def _user_for(self, token: str | None) -> str | None:
        if not token:
            return None
        found = None
        for tok, name in self.tokens.items():  # 상수시간 비교
            if hmac.compare_digest(tok.encode(), token.encode()):
                found = name
        return found

    @staticmethod
    def _extract_token(scope) -> str | None:
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        auth = headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            return auth[7:].strip()
        if headers.get("x-api-key"):
            return headers["x-api-key"].strip()
        qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        return (qs.get("key") or [None])[0]

    @staticmethod
    async def _send_json(send, status: int, body: dict) -> None:
        raw = json.dumps(body, ensure_ascii=False).encode()
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", b"application/json; charset=utf-8"),
                                (b"content-length", str(len(raw)).encode())]})
        await send({"type": "http.response.body", "body": raw})

    def _log(self, scope, user: str, body: bytes) -> None:
        try:
            msg = json.loads(body) if body else None
        except ValueError:
            msg = None
        items = msg if isinstance(msg, list) else [msg] if isinstance(msg, dict) else []
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        ip = headers.get("cf-connecting-ip") or (scope.get("client") or ["?"])[0]
        now = datetime.now(KST)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"usage-{now:%Y-%m}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            for m in items:
                if not isinstance(m, dict):
                    continue
                params = m.get("params") or {}
                rec = {"ts": now.isoformat(timespec="seconds"), "user": user, "ip": ip, "method": m.get("method")}
                if m.get("method") == "tools/call":
                    rec["tool"] = params.get("name")
                    rec["arg_keys"] = sorted((params.get("arguments") or {}).keys())  # 값은 저장하지 않음
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        if scope.get("path") == "/health":
            return await self._send_json(send, 200, {"status": "ok", "server": SERVER_NAME})

        user = self._user_for(self._extract_token(scope))
        if user is None:
            return await self._send_json(send, 401, {"error": "인증 필요 — 발급받은 접속 토큰을 넣어 주세요"})

        if scope.get("method") != "POST":
            return await self.app(scope, receive, send)

        chunks, size = [], 0
        while True:
            msg = await receive()
            if msg["type"] == "http.disconnect":
                return
            chunk = msg.get("body", b"")
            size += len(chunk)
            if size > MAX_BODY:
                return await self._send_json(send, 413, {"error": "요청이 너무 큽니다"})
            chunks.append(chunk)
            if not msg.get("more_body"):
                break
        body = b"".join(chunks)
        try:
            self._log(scope, user, body)
        except OSError:
            pass  # 로그 실패가 계산을 막지 않도록

        sent = False

        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


def build_http_app(settings: Settings):
    """public 모드 HTTP 앱 — Cloudflare Tunnel 뒤에서 127.0.0.1로 띄운다."""
    from mcp.server.transport_security import TransportSecuritySettings

    mcp = build_server(settings)
    hosts = ["127.0.0.1:*", "localhost:*", "127.0.0.1", "localhost"]
    origins = ["http://127.0.0.1:*", "http://localhost:*", "https://claude.ai"]
    for h in settings.public_hosts:
        hosts += [h, f"{h}:*"]
        origins += [f"https://{h}"]
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True,
                                         allowed_hosts=hosts, allowed_origins=origins)
    app = mcp.streamable_http_app(streamable_http_path="/mcp", stateless_http=True,
                                  json_response=True, transport_security=security, host=settings.host)
    return AccessGate(app, settings)


# ───────────────────────── 실행 ─────────────────────────

def main(argv: list[str] | None = None) -> None:
    load_dotenv()
    settings = Settings.from_env()
    p = argparse.ArgumentParser(prog=SERVER_NAME, description="위드플러스 세금계산기 MCP 서버")
    p.add_argument("--mode", choices=["local", "public"], default=settings.mode,
                   help="local=내 PC 전용(stdio), public=외부 공개(HTTP+토큰)")
    p.add_argument("--host", default=settings.host)
    p.add_argument("--port", type=int, default=settings.port)
    a = p.parse_args(argv)
    settings.mode, settings.host, settings.port = a.mode, a.host, a.port

    if settings.mode == "local":
        build_server(settings).run("stdio")
        return

    if not settings.tokens:
        sys.exit("[중단] public 모드는 접속 토큰이 필요합니다. .env 의 WITHPLUS_TOKENS 를 채우세요.")
    if not settings.public_hosts:
        print("[경고] WITHPLUS_PUBLIC_HOSTS 가 비어 있어 localhost 접속만 허용됩니다.", file=sys.stderr)
    import uvicorn
    print(f"[위드플러스 세금계산기] http://{settings.host}:{settings.port}/mcp  "
          f"(허용 도메인: {', '.join(settings.public_hosts) or '없음'}, 토큰 {len(settings.tokens)}개)", file=sys.stderr)
    uvicorn.run(build_http_app(settings), host=settings.host, port=settings.port,
                proxy_headers=True, forwarded_allow_ips="127.0.0.1")


if __name__ == "__main__":
    main()
