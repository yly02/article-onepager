#!/usr/bin/env python3
"""Build a deterministic, self-testable article-onepager ZIP."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
REQUIRED = (
    "SKILL.md",
    "agents/openai.yaml",
    "references/editorial-guide.md",
    "references/integration-contract.md",
    "references/installation.md",
    "scripts/run.py",
    "scripts/check_environment.py",
    "scripts/onepager_mode.py",
    "scripts/onepager_prompt.py",
    "scripts/onepager_quality.py",
    "scripts/onepager_renderer.py",
    "tests/test_onepager.py",
)


def package(output: Path) -> Path:
    missing = [name for name in REQUIRED if not (SKILL_ROOT / name).is_file()]
    if missing:
        raise ValueError("缺少打包文件：" + ", ".join(missing))
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path for path in SKILL_ROOT.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".zip"}
    )
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = Path("article-onepager") / path.relative_to(SKILL_ROOT)
            info = zipfile.ZipInfo(str(relative), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.name in {"run.py", "package_skill.py"} else 0o644) << 16
            archive.writestr(info, path.read_bytes())
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="打包 article-onepager Skill")
    parser.add_argument("--output", "-o", default="article-onepager.zip")
    args = parser.parse_args()
    print(package(Path(args.output)))


if __name__ == "__main__":
    main()
