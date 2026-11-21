"""위드플러스 세금계산기를 Claude Desktop 확장 파일(.mcpb)로 묶는다.

무료 요금제 등 '설정 파일 등록' 방식이 안 되는 PC용. 직원은 .mcpb 파일을 더블클릭(또는 Claude Desktop
설정 → 확장 프로그램에 끌어다 놓기)만 하면 된다. Python·uv는 Claude Desktop이 알아서 준비한다(uv 런타임).

빌드(저장소 최상위에서, Node.js 필요):
    python withplus/deploy/build_mcpb.py
결과: withplus/dist/withplus-tax-<버전>.mcpb
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # 저장소 최상위
WP = ROOT / "withplus"
STAGE = WP / "build" / "mcpb"
DIST = WP / "dist"

SERVER_PY = '''"""위드플러스 세금계산기 — Claude Desktop 확장 진입점(내 PC 모드)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from withplus_tax.server import main  # noqa: E402

main(["--mode", "local"])
'''


def upstream_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^version\s*=\s*"([^"]+)"', text, re.M).group(1)


def upstream_deps() -> list[str]:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    block = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.M | re.S).group(1)
    deps = re.findall(r'"([^"]+)"', block)
    return [d for d in deps if not d.startswith("uvicorn")]  # 내 PC 모드(stdio)에는 불필요


def make_icon(path: Path) -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return
    im = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([8, 8, 248, 248], radius=48, fill=(29, 91, 120, 255))
    font = None
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf"):
        try:
            font = ImageFont.truetype(name, 120)
            break
        except OSError:
            continue
    d.text((128, 132), "W+", fill=(255, 255, 255, 255), anchor="mm", font=font or ImageFont.load_default())
    im.save(path)


def stage() -> str:
    version = upstream_version()
    ext_version = f"{version.split('.')[0]}.{version.split('.')[1]}.{version.split('.')[2]}"
    if STAGE.exists():
        shutil.rmtree(STAGE)
    src = STAGE / "src"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".env", "logs")
    shutil.copytree(ROOT / "korean_tax_calc_mcp", src / "korean_tax_calc_mcp", ignore=ignore)
    shutil.copytree(WP / "withplus_tax", src / "withplus_tax", ignore=ignore)
    (src / "server.py").write_text(SERVER_PY, encoding="utf-8")
    shutil.copy2(ROOT / "LICENSE", STAGE / "LICENSE")
    shutil.copy2(WP / "NOTICE", STAGE / "NOTICE")

    deps = ",\n    ".join(f'"{d}"' for d in upstream_deps())
    (STAGE / "pyproject.toml").write_text(
        f'[project]\nname = "withplus-tax-mcpb"\nversion = "{ext_version}"\n'
        f'requires-python = ">=3.10"\ndependencies = [\n    {deps},\n]\n', encoding="utf-8")
    (STAGE / ".mcpbignore").write_text(".venv/\n__pycache__/\n*.pyc\n", encoding="utf-8")
    make_icon(STAGE / "icon.png")

    manifest = {
        "manifest_version": "0.4",
        "name": "withplus-tax",
        "display_name": "위드플러스 세금계산기",
        "version": ext_version,
        "description": "법인세·소득세·양도·상속증여·부가세·가산세 계산 도구 93개 — 코드로 계산하고 근거 조문을 붙입니다.",
        "long_description": (
            "세무법인 위드플러스 내부용 세금계산기입니다. 계산 엔진은 Upstage korean-tax-calc-mcp(MIT)이며, "
            "연도별 세율표(2016~2026)로 조문 순서대로 계산하고 결과마다 근거 조문을 붙입니다. "
            "계산 결과는 검토 보조자료이며 사실관계 판단은 세무사 확인이 필요합니다."
        ),
        "author": {"name": "세무법인 위드플러스", "url": "https://www.withplus-biz.com"},
        "repository": {"type": "git", "url": "https://github.com/socker008-hub/withplus-tax-calc"},
        "license": "MIT",
        "server": {
            "type": "uv",
            "entry_point": "src/server.py",
            "mcp_config": {
                "command": "uv",
                "args": ["run", "--directory", "${__dirname}", "src/server.py"],
            },
        },
        "tools_generated": True,
        "compatibility": {
            "platforms": ["win32", "darwin", "linux"],
            "runtimes": {"python": ">=3.10"},
        },
        "keywords": ["tax", "korea", "세금", "세무", "위드플러스"],
    }
    if (STAGE / "icon.png").exists():
        manifest["icon"] = "icon.png"
    (STAGE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return ext_version


def pack(ext_version: str) -> Path:
    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / f"withplus-tax-{ext_version}.mcpb"
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if not npx:
        sys.exit("[중단] Node.js(npx)가 필요합니다: https://nodejs.org")
    subprocess.run([npx, "-y", "@anthropic-ai/mcpb@2.1.2", "validate", str(STAGE / "manifest.json")], check=True)
    subprocess.run([npx, "-y", "@anthropic-ai/mcpb@2.1.2", "pack", str(STAGE), str(out)], check=True)
    return out


if __name__ == "__main__":
    v = stage()
    print(f"staged {STAGE} (v{v})")
    if "--no-pack" not in sys.argv:
        print(f"built {pack(v)}")
