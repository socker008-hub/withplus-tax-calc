"""설정 — .env 파일 또는 환경변수에서 읽는다. 비밀값(토큰)은 코드에 쓰지 않는다."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_FOOTER = (
    "본 결과는 세무법인 위드플러스 세금계산기(코드 계산)의 검토 보조자료입니다. "
    "실제 신고·의사결정 전 세무사 검토가 필요합니다. 문의 02-438-7001 · www.withplus-biz.com"
)

# 공개(원격) 모드에서 끄는 도구 — 서버 PC의 파일을 읽거나(PDF 경로) 서버 PC에 파일을 쓰는(엑셀 저장) 도구
SERVER_FILE_TOOLS = ("extract_relations", "tunnelling_from_pdf", "return_precheck_pdf", "export_workbook")


def load_dotenv(path: str | os.PathLike | None = None) -> None:
    """간단한 .env 로더(외부 패키지 없이). 이미 설정된 환경변수는 덮어쓰지 않는다."""
    p = Path(path) if path else Path(__file__).resolve().parents[1] / ".env"
    if not p.is_file():
        return
    for raw in p.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def parse_tokens(raw: str) -> dict[str, str]:
    """'이름:토큰,이름2:토큰2' → {토큰: 이름}. 이름 없이 토큰만 쓰면 이름은 'user1'…"""
    out: dict[str, str] = {}
    for i, part in enumerate(p.strip() for p in raw.split(",") if p.strip()):
        if ":" in part:
            name, tok = part.split(":", 1)
        else:
            name, tok = f"user{i + 1}", part
        tok = tok.strip()
        if len(tok) < 24:
            raise ValueError(f"토큰이 너무 짧습니다({name.strip()}) — 24자 이상 무작위 문자열을 쓰세요")
        out[tok] = name.strip()
    return out


@dataclass
class Settings:
    mode: str = "local"                      # local | public
    host: str = "127.0.0.1"
    port: int = 8001
    public_hosts: list[str] = field(default_factory=list)   # 예: mcp.withplustax.com
    tokens: dict[str, str] = field(default_factory=dict)    # {토큰: 사용자명}
    footer: str = DEFAULT_FOOTER                            # 빈 문자열이면 끔
    log_dir: Path = Path("logs")

    @classmethod
    def from_env(cls) -> "Settings":
        hosts = [h.strip() for h in os.environ.get("WITHPLUS_PUBLIC_HOSTS", "").split(",") if h.strip()]
        footer = os.environ.get("WITHPLUS_FOOTER")
        return cls(
            mode=os.environ.get("WITHPLUS_MODE", "local").strip().lower(),
            host=os.environ.get("WITHPLUS_HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", os.environ.get("WITHPLUS_PORT", "8001"))),
            public_hosts=hosts,
            tokens=parse_tokens(os.environ.get("WITHPLUS_TOKENS", "")),
            footer=DEFAULT_FOOTER if footer is None else footer,
            log_dir=_resolve(os.environ.get("WITHPLUS_LOG_DIR", "logs")),
        )


def _resolve(p: str) -> Path:
    """상대경로는 withplus 폴더 기준(어느 폴더에서 실행해도 같은 곳에 로그가 쌓이도록)."""
    path = Path(p)
    return path if path.is_absolute() else Path(__file__).resolve().parents[1] / path
