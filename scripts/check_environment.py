#!/usr/bin/env python3
"""Portable preflight checks for article-onepager installations."""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import re
import sqlite3
import sys
from shutil import which
from pathlib import Path
from typing import Any


MIN_PYTHON = (3, 10)
SHARED_ENV = "ARTICLE_DISTILLER_ROOT"
SHARED_RELATIVE = Path("scripts") / "distill.py"
REQUIRED_SHARED_FILES = (
    Path("scripts/distill.py"),
    Path("scripts/distiller.py"),
    Path("scripts/fetcher.py"),
    Path("scripts/editorial_quality.py"),
    Path("requirements.txt"),
)
PYTHON_MODULES = {
    "trafilatura": "trafilatura",
    "lxml_html_clean": "lxml-html-clean",
    "openai": "openai",
    "pypdf": "pypdf",
    "docx": "python-docx",
}


def _candidate_shared_roots(skill_root: Path | None = None) -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get(SHARED_ENV, "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    if skill_root:
        candidates.append(skill_root.expanduser().resolve().parent / "article-distiller")
    home = Path.home()
    candidates.extend([
        home / ".workbuddy/skills/article-distiller",
        home / ".codex/skills/article-distiller",
        home / ".local/share/codex/skills/article-distiller",
    ])
    result: list[Path] = []
    seen: set[str] = set()
    for path in candidates:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def resolve_shared_root(skill_root: Path | None = None) -> Path | None:
    for candidate in _candidate_shared_roots(skill_root):
        if (candidate / SHARED_RELATIVE).is_file():
            return candidate.resolve()
    return None


def _module_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _ccswitch_has_provider(db_path: Path) -> bool:
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
            rows = connection.execute(
                "select settings_config from providers where settings_config is not null"
            ).fetchall()
    except (OSError, sqlite3.Error):
        return False
    key_names = {"api_key", "apikey", "key", "token", "openai_api_key", "openaiapikey"}
    for (raw,) in rows:
        try:
            settings = json.loads(raw or "{}")
        except (TypeError, ValueError):
            continue
        if not isinstance(settings, dict):
            continue
        flattened = {str(key).lower().replace("-", "_"): value for key, value in settings.items()}
        if any(str(flattened.get(name) or "").strip() for name in key_names):
            return True
        config_text = settings.get("config") if isinstance(settings.get("config"), str) else ""
        if re.search(r"(?im)^\s*(?:api_key|apiKey|token)\s*=\s*['\"]?\S+", config_text):
            return True
    return False


def _llm_configured(config_path: str | None = None) -> tuple[bool, str]:
    if os.environ.get("DISTILL_LLM_KEY", "").strip():
        return True, "DISTILL_LLM_KEY"
    if config_path:
        path = Path(config_path).expanduser()
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return False, f"配置文件不可读：{path}"
            if isinstance(value, dict) and str(value.get("api_key") or "").strip():
                return True, str(path)
            return False, f"配置文件缺少 api_key：{path}"
        return False, f"配置文件不存在：{path}"
    ccswitch_path = Path.home() / ".cc-switch/cc-switch.db"
    if _ccswitch_has_provider(ccswitch_path):
        return True, str(ccswitch_path)
    return False, "DISTILL_LLM_KEY、--config 或 ccswitch 当前提供商"


def check_environment(
    *,
    skill_root: Path | None = None,
    require_llm: bool = True,
    config_path: str | None = None,
    input_path: str | None = None,
) -> dict[str, Any]:
    skill_root = (skill_root or Path(__file__).resolve().parents[1]).resolve()
    shared_root = resolve_shared_root(skill_root)
    required_modules = ["trafilatura", "lxml_html_clean"]
    suffix = Path(input_path).suffix.lower() if input_path else ""
    if suffix == ".pdf":
        required_modules.append("pypdf")
    elif suffix == ".docx":
        required_modules.append("docx")
    elif suffix == ".doc":
        required_modules.append("docx")
    if require_llm:
        required_modules.append("openai")
    checks: list[dict[str, Any]] = []

    python_ok = sys.version_info[:2] >= MIN_PYTHON
    checks.append({
        "name": "python",
        "ok": python_ok,
        "detail": platform.python_version(),
        "required": "3.10+",
    })
    checks.append({
        "name": "shared_engine",
        "ok": shared_root is not None,
        "detail": str(shared_root) if shared_root else "未找到 article-distiller/scripts/distill.py",
        "required": f"设置 {SHARED_ENV} 或安装到 ~/.workbuddy/skills/article-distiller",
    })
    for module in dict.fromkeys(required_modules):
        available = _module_available(module)
        checks.append({
            "name": module,
            "ok": available,
            "detail": "已安装" if available else f"缺少 Python 模块：{module}",
            "required": (
                ""
                if available
                else f"{sys.executable} -m pip install {PYTHON_MODULES[module]}"
            ),
        })
    if shared_root:
        missing_shared = [str(path) for path in REQUIRED_SHARED_FILES if not (shared_root / path).is_file()]
        checks.append({
            "name": "shared_files",
            "ok": not missing_shared,
            "detail": "完整" if not missing_shared else "缺少：" + ", ".join(missing_shared),
            "required": "重新安装 article-distiller 共享引擎",
        })
    if suffix == ".doc":
        soffice_ok = which("soffice") is not None
        checks.append({
            "name": "soffice",
            "ok": soffice_ok,
            "detail": "已找到 LibreOffice" if soffice_ok else "读取 .doc 需要 LibreOffice 命令 soffice",
            "required": "安装 LibreOffice，或将 .doc 另存为 .docx",
        })
    if require_llm:
        configured, detail = _llm_configured(config_path)
        checks.append({
            "name": "llm_config",
            "ok": configured,
            "detail": detail if configured else f"未检测到可用 LLM 配置（需要 {detail}）",
            "required": "设置 DISTILL_LLM_KEY，或使用 --config /path/to/config.json",
        })

    errors = [item for item in checks if not item["ok"]]
    return {
        "ok": not errors,
        "python": sys.executable,
        "skill_root": str(skill_root),
        "shared_root": str(shared_root) if shared_root else None,
        "require_llm": require_llm,
        "checks": checks,
        "errors": errors,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "article-onepager 环境检查",
        f"Python：{report['python']}",
        f"Skill：{report['skill_root']}",
    ]
    for item in report["checks"]:
        mark = "通过" if item["ok"] else "缺少"
        lines.append(f"- {mark} {item['name']}：{item['detail']}")
        if not item["ok"]:
            lines.append(f"  处理：{item['required']}")
    if report["ok"]:
        lines.append("结果：环境满足当前运行模式。")
    else:
        lines.append("结果：请先处理上面的缺项；检查不会输出或记录 API key。")
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="检查 article-onepager 运行环境")
    parser.add_argument("--config", help="LLM config.json 路径")
    parser.add_argument("--input", help="将要读取的本地文件路径，用于检查 PDF/Word 专用依赖")
    parser.add_argument("--no-llm", action="store_true", help="仅检查抓取和渲染环境")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args()
    report = check_environment(
        require_llm=not args.no_llm,
        config_path=args.config,
        input_path=args.input,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
