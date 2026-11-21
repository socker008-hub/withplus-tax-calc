"""Claude Desktop 설정 파일에 위드플러스 세금계산기(withplus-tax)를 등록하고 계산 테스트를 한다.

staff_setup.bat 이 자동으로 실행한다. 직접 실행할 때(withplus 폴더에서):
    uv run python deploy\\register_claude_desktop.py

- 기존 설정(다른 MCP 서버, 앱 환경설정)은 그대로 두고 mcpServers.withplus-tax 한 항목만 넣거나 바꾼다.
- 고치기 전에 원본을 .bak-날짜시각 파일로 백업한다.
- 기존 파일이 JSON 형식이 깨져 있으면 손대지 않고 중단한다(덮어써서 설정을 잃지 않도록).
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

SERVER_KEY = "withplus-tax"


def config_candidates() -> list[Path]:
    """Claude Desktop 설정 파일 위치 — 일반 설치본과 Microsoft Store(MSIX) 설치본."""
    paths: list[Path] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        paths.append(Path(appdata) / "Claude" / "claude_desktop_config.json")
    local = os.environ.get("LOCALAPPDATA")
    if local:
        pkgs = Path(local) / "Packages"
        if pkgs.is_dir():
            paths += sorted(pkgs.glob("Claude_*/LocalCache/Roaming/Claude/claude_desktop_config.json"))
    return paths


def find_uv() -> str:
    found = shutil.which("uv")
    if found:
        return str(Path(found).resolve())
    home = Path(os.environ.get("USERPROFILE", str(Path.home())))
    guess = home / ".local" / "bin" / ("uv.exe" if os.name == "nt" else "uv")
    if guess.is_file():
        return str(guess)
    raise SystemExit("[중단] uv 를 찾지 못했습니다. staff_setup.bat 을 다시 실행하세요.")


def server_entry(project: Path, uv: str) -> dict:
    return {"command": uv,
            "args": ["run", "--project", str(project), "withplus-tax-calc", "--mode", "local"]}


def merge_into(path: Path, entry: dict) -> str:
    """설정 파일 하나에 등록. 결과 문구를 돌려준다."""
    if path.is_file():
        raw = path.read_text(encoding="utf-8-sig")
        try:
            data = json.loads(raw) if raw.strip() else {}
        except ValueError as e:
            raise RuntimeError(f"설정 파일 형식이 깨져 있어 손대지 않았습니다: {path}\n  ({e})\n"
                               "  메모장으로 열어 마지막에 덧붙인 내용을 지운 뒤 다시 실행하세요.")
        if not isinstance(data, dict):
            raise RuntimeError(f"설정 파일 최상위가 {{ }} 형식이 아니어서 손대지 않았습니다: {path}")
        backup = path.with_name(f"{path.name}.bak-{datetime.now():%Y%m%d%H%M%S}")
        shutil.copy2(path, backup)
        servers = data.get("mcpServers")
        if not isinstance(servers, dict):
            servers = {}
        action = "갱신" if SERVER_KEY in servers else "추가"
        servers[SERVER_KEY] = entry
        data = {"mcpServers": servers, **{k: v for k, v in data.items() if k != "mcpServers"}}
        note = f"{action} (백업: {backup.name})"
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"mcpServers": {SERVER_KEY: entry}}
        note = "새로 만듦"
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    json.loads(text)  # 저장 전 형식 재확인
    path.write_text(text, encoding="utf-8")
    return note


def self_test() -> int:
    """퇴직금 1억·근속 15년·2026 퇴직 → 2,175,000원이 나오는지 확인."""
    from withplus_tax.config import Settings
    from withplus_tax.server import build_server

    mcp = build_server(Settings(mode="local"))
    r = asyncio.run(mcp.call_tool("retirement_income_tax",
                                  {"income": 100_000_000, "years_of_service": 15, "retire_year": 2026}))
    data = json.loads(r.content[0].text)
    tax = data["결과"]["퇴직소득세"]
    tools = len(asyncio.run(mcp.list_tools()))
    ok = tax == 2_175_000
    print(f"  계산 테스트: 퇴직소득세 {tax:,}원 (정답 2,175,000원) → {'정상' if ok else '확인 필요'}")
    print(f"  사용 가능한 도구: {tools}개")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--project", default=str(Path(__file__).resolve().parents[1]),
                   help="withplus 폴더 경로(기본: 이 파일 기준)")
    a = p.parse_args(argv)
    project = Path(a.project).resolve()
    entry = server_entry(project, find_uv())

    paths = config_candidates()
    existing = [x for x in paths if x.is_file()]
    targets = existing or paths[:1]
    if not targets:
        print("[중단] Claude Desktop 설정 위치(APPDATA)를 찾지 못했습니다.")
        return 2

    failed = False
    for path in targets:
        try:
            print(f"  설정 파일: {path}\n    → {merge_into(path, entry)}")
        except (RuntimeError, OSError) as e:
            failed = True
            print(f"[오류] {e}")
    if failed:
        return 3
    return self_test()


if __name__ == "__main__":
    sys.exit(main())
