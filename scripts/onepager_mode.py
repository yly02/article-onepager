"""article-distiller mode adapter exported by article-onepager."""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def _load_local(name: str):
    path = SCRIPT_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"article_onepager_{name}", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"无法加载 article-onepager 模块：{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_prompt = _load_local("onepager_prompt")
_quality = _load_local("onepager_quality")
_renderer = _load_local("onepager_renderer")

SYSTEM_PROMPT = _prompt.SYSTEM_PROMPT
RESEARCH_PROMPT = _prompt.RESEARCH_PROMPT
EDITORIAL_REVIEW_PROMPT = _prompt.EDITORIAL_REVIEW_PROMPT
audit_distilled = _quality.audit_distilled
choose_preferred = _quality.choose_preferred
assert_publishable = _quality.assert_publishable
render_html = _renderer.render_html
render_markdown = _renderer.render_markdown


MODE = "onepager"
ENTRYPOINT = str(SCRIPT_DIR / "run.py")

# One-pagers favor bounded latency: research once, write from the compact ledger,
# and ask the model to review only when the deterministic gate rejects the draft.
LLM_TIMEOUT_SECONDS = 180
LLM_MAX_RETRIES = 1
LLM_STREAM = True
LLM_RETRY_DELAY_SECONDS = 8
LLM_RETRY_MAX_WAIT_SECONDS = 30
EVIDENCE_SOURCE_LIMIT = 5
EVIDENCE_CHAR_LIMIT = 6000
REPOSITORY_CONTEXT_CHAR_LIMIT = 3000
RESEARCH_LEDGER_MAX_CHARS = 24000
COMPACT_SOURCE_REGISTRY = True
DRAFT_CONTEXT_MODE = "research-ledger"
EDITORIAL_REVIEW_POLICY = "on-failure"
RESEARCH_FAILURE_FALLBACK = True
