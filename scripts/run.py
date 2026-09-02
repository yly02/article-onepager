#!/usr/bin/env python3
"""Fixed entrypoint for the article-onepager skill."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

# Keep the wrapper importable when the shared test harness loads it by file path.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_environment import check_environment, format_report, resolve_shared_root

MODE = "onepager"
MODE_ADAPTER = Path(__file__).resolve().with_name("onepager_mode.py")


def _has_option(argv: list[str], name: str) -> bool:
    return any(arg == name or arg.startswith(name + "=") for arg in argv)


def _config_path(argv: list[str]) -> str | None:
    for index, value in enumerate(argv):
        if value.startswith("--config="):
            return value.split("=", 1)[1]
        if value == "--config" and index + 1 < len(argv):
            return argv[index + 1]
    return None


def _input_path(argv: list[str]) -> str | None:
    for index, value in enumerate(argv):
        if value.startswith("--from-text="):
            return value.split("=", 1)[1]
        if value == "--from-text" and index + 1 < len(argv):
            return argv[index + 1]
    if argv and not argv[0].startswith("-") and Path(argv[0]).is_file():
        return argv[0]
    return None


def build_shared_argv(argv: list[str]) -> list[str]:
    if any(arg == "--format" or arg.startswith("--format=") for arg in argv):
        raise ValueError("article-onepager 固定输出 onepager；请移除 --format")
    if any(arg == "--mode-adapter" or arg.startswith("--mode-adapter=") for arg in argv):
        raise ValueError("article-onepager 固定使用 Skill 自有实现；请移除 --mode-adapter")
    defaults = []
    if not _has_option(argv, "--repo-file-limit"):
        defaults.extend(["--repo-file-limit", "3"])
    return [*argv, *defaults, "--format", MODE, "--mode-adapter", str(MODE_ADAPTER)]


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--check" in args:
        check_args = [value for value in args if value != "--check"]
        allowed_config = (
            not check_args
            or (len(check_args) == 1 and check_args[0].startswith("--config="))
            or (len(check_args) == 2 and check_args[0] == "--config")
        )
        if not allowed_config:
            raise SystemExit("--check 只能与 --config /path/to/config.json 一起使用")
        report = check_environment(require_llm=True, config_path=_config_path(check_args))
        print(format_report(report))
        raise SystemExit(0 if report["ok"] else 1)
    shared_root = resolve_shared_root(Path(__file__).resolve().parents[1])
    source_only = "--source-only" in args
    render_mode = "--render" in args
    config_path = _config_path(args)
    report = check_environment(
        skill_root=Path(__file__).resolve().parents[1],
        require_llm=not source_only and not render_mode,
        config_path=config_path,
        input_path=_input_path(args) if not render_mode else None,
    )
    print(format_report(report), file=sys.stderr)
    if not report["ok"]:
        raise SystemExit(1)
    shared_script = shared_root / "scripts/distill.py"
    try:
        shared_argv = build_shared_argv(args)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    sys.path.insert(0, str(shared_script.parent))
    sys.argv = [str(shared_script), *shared_argv]
    runpy.run_path(str(shared_script), run_name="__main__")


if __name__ == "__main__":
    main()
