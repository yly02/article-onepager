#!/usr/bin/env python3
"""Independent behavior tests for article-onepager."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


SKILL_ROOT = Path(__file__).resolve().parents[1]
SHARED_SCRIPTS = Path.home() / ".workbuddy/skills/article-distiller/scripts"
sys.path.insert(0, str(SHARED_SCRIPTS))
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from onepager_mode import (  # noqa: E402
    COMPACT_SOURCE_REGISTRY,
    DRAFT_CONTEXT_MODE,
    EDITORIAL_REVIEW_PROMPT,
    EDITORIAL_REVIEW_POLICY,
    EVIDENCE_CHAR_LIMIT,
    EVIDENCE_SOURCE_LIMIT,
    LLM_MAX_RETRIES,
    LLM_STREAM,
    LLM_TIMEOUT_SECONDS,
    RESEARCH_PROMPT,
    RESEARCH_LEDGER_MAX_CHARS,
    SYSTEM_PROMPT,
    audit_distilled,
    render_html,
    render_markdown,
)
from check_environment import check_environment, format_report, resolve_shared_root  # noqa: E402
from distiller import _build_draft_context, _call_json  # noqa: E402
from package_skill import package  # noqa: E402
from run import MODE_ADAPTER, _config_path, build_shared_argv  # noqa: E402


def sample() -> tuple[dict, dict]:
    fact = (
        "研究团队公开了一套新的评测流程。它把准备、执行和复核分开记录，并保留每一步的人工条件，"
        "因此读者能看清结果来自模型能力还是流程设计。原始材料同时提醒，这只是一次受控测试，不能直接外推到所有生产环境。"
    )
    mechanism = (
        "真正的变化不是单项分数更高，而是证据链更完整。每个结论都回到具体任务、输入和复核记录，"
        "失败案例也没有被删掉。这样做降低了只看亮眼结果造成的误判，也让后续复测知道该复现哪些条件。"
    )
    boundary = (
        "目前仍缺少跨机构复测和更长时间的运行数据。对读者而言，合理动作是先把它当作方法样例，"
        "观察独立团队能否在相同条件下得到一致结果，再决定是否迁移到自己的工作流。发布方结论仍需与独立证据分开阅读。"
    )
    research = {
        "claims": [
            {"id": "c1", "claim": "研究团队公开了分步记录的评测流程，并保留人工条件。", "importance": "high"},
            {"id": "c2", "claim": "这套流程保留失败案例和复核记录，以便后续复测。", "importance": "high"},
            {"id": "c3", "claim": "当前缺少跨机构复测和长期运行数据。", "importance": "high"},
        ]
    }
    distilled = {
        "distilled_title": "一套评测流程开始把失败也写进证据链",
        "category_tags": ["评测透明度", "证据链", "复现边界"],
        "source_bias_declaration": "材料由研究团队发布，目前没有独立跨机构复测。",
        "content_gap": "",
        "one_pager": {
            "layout": "narrative-spine",
            "lead": "一套新的评测流程把准备、执行和复核拆开记录。变化不在于多一个漂亮分数，而在于读者第一次能沿着证据链检查结果怎样产生。",
            "lead_claim_ids": ["c1"],
            "key_sections": [
                {
                    "role": "fact", "subtitle": "评测过程终于能被追溯", "content": fact * 2, "claim_ids": ["c1"],
                    "visual_relation": "transition",
                    "visual_items": [
                        {"label": "混合记录", "detail": "步骤与人工条件难以分开"},
                        {"label": "分步追溯", "detail": "准备、执行和复核分别记录"},
                    ],
                },
                {
                    "role": "mechanism", "subtitle": "失败记录比单项高分更重要", "content": mechanism * 2, "claim_ids": ["c2"],
                    "visual_relation": "loop",
                    "visual_items": [
                        {"label": "具体任务", "detail": "记录输入与执行条件"},
                        {"label": "保留失败", "detail": "不删除不理想结果"},
                        {"label": "后续复测", "detail": "按相同条件重新验证"},
                    ],
                },
                {
                    "role": "boundary", "subtitle": "下一步要等独立团队复测", "content": boundary * 2, "claim_ids": ["c3"],
                    "visual_relation": "bottleneck",
                    "visual_items": [
                        {"label": "发布方结果", "detail": "目前只有受控测试"},
                        {"label": "独立证据", "detail": "仍缺跨机构长期复测"},
                    ],
                },
            ],
            "references": [{"title": "原始研究", "url": "https://example.com/research"}],
        },
        "fact_check": [
            {
                "claim": "研究团队公开了分步评测流程并保留人工条件、失败案例和复核记录。",
                "verdict": "原文声称",
                "note": "当前缺少跨机构复测和长期运行数据。",
                "evidence": [{"url": "https://example.com/research", "source_type": "original", "publisher": "研究团队"}],
            }
        ],
        "source_notes": "只能确认发布方材料的结构与说法，尚不能确认外部复现结果。",
        "editorial_coverage": {"covered_claim_ids": ["c1", "c2", "c3"], "omitted_claims": []},
    }
    return distilled, research


def test_prompt_and_wrapper_are_skill_owned():
    assert "claims 总数控制在 8-12 条" in RESEARCH_PROMPT
    assert "importance=high 严格控制在 4-7 条" in RESEARCH_PROMPT
    assert '"role": "fact|mechanism|impact|boundary"' in SYSTEM_PROMPT
    assert '"layout": "narrative-spine"' in SYSTEM_PROMPT
    assert '"visual_relation": "none|contrast|transition|converge|bottleneck|loop|metrics|matrix"' in SYSTEM_PROMPT
    assert '"visual_columns"' in SYSTEM_PROMPT
    assert "500-800" in EDITORIAL_REVIEW_PROMPT
    assert "只有 matrix 可以保留 visual_columns" in EDITORIAL_REVIEW_PROMPT
    assert "不得把正文压缩到 500 字以下" in EDITORIAL_REVIEW_PROMPT
    argv = build_shared_argv(["https://example.com/research", "--source-only"])
    assert argv[-4:] == ["--format", "onepager", "--mode-adapter", str(MODE_ADAPTER)]
    assert argv[-6:-4] == ["--repo-file-limit", "3"]
    assert _config_path(["--config=/tmp/config.json"]) == "/tmp/config.json"
    assert _config_path(["--config", "/tmp/config.json"]) == "/tmp/config.json"
    explicit = build_shared_argv(["https://example.com/research", "--repo-file-limit=5"])
    assert explicit.count("--repo-file-limit=5") == 1
    assert "3" not in explicit[:-4]
    for bad in (["--format", "full"], ["--mode-adapter", "/tmp/x.py"]):
        try:
            build_shared_argv(bad)
            raise AssertionError("wrapper must reject implementation overrides")
        except ValueError:
            pass


def test_environment_check_is_actionable_and_does_not_require_llm_for_render():
    report = check_environment(
        skill_root=SKILL_ROOT,
        require_llm=False,
    )
    assert report["shared_root"]
    assert report["require_llm"] is False
    rendered = format_report(report)
    assert "article-onepager 环境检查" in rendered
    assert "API key" not in rendered
    assert resolve_shared_root(SKILL_ROOT) == Path(report["shared_root"])
    pdf_report = check_environment(skill_root=SKILL_ROOT, require_llm=False, input_path="report.pdf")
    assert any(item["name"] == "pypdf" for item in pdf_report["checks"])
    docx_report = check_environment(skill_root=SKILL_ROOT, require_llm=False, input_path="report.docx")
    assert any(item["name"] == "docx" for item in docx_report["checks"])


def test_latency_budget_and_compact_draft_context():
    assert LLM_TIMEOUT_SECONDS == 180
    assert LLM_MAX_RETRIES == 1
    assert LLM_STREAM is True
    assert EVIDENCE_SOURCE_LIMIT == 5
    assert EVIDENCE_CHAR_LIMIT == 6000
    assert RESEARCH_LEDGER_MAX_CHARS == 24000
    assert COMPACT_SOURCE_REGISTRY is True
    assert DRAFT_CONTEXT_MODE == "research-ledger"
    assert EDITORIAL_REVIEW_POLICY == "on-failure"

    article = SimpleNamespace(
        title="来源文章", author="作者", date="2026-08-25",
        url="https://example.com/research",
    )
    evidence = [SimpleNamespace(
        title="独立复测", url="https://evidence.example/report", source_type="independent",
    )]
    research = {"claims": [{"id": "c1", "claim": "账本保留的关键结论", "importance": "high"}]}
    context = _build_draft_context(
        article, evidence, research, "不应重复发送的完整原文", mode_adapter=sys.modules["onepager_mode"]
    )
    assert "不应重复发送的完整原文" not in context
    assert "账本保留的关键结论" in context
    assert "https://example.com/research" in context
    assert "https://evidence.example/report" in context


def test_controlled_retry_is_bounded():
    class RetryableError(Exception):
        status_code = 524
        response = SimpleNamespace(headers={"retry-after": "120"})

    class FakeCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RetryableError("origin timeout")
            message = SimpleNamespace(content='{"ok": true}')
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    completions = FakeCompletions()
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    result = _call_json(
        client,
        {
            "model": "test-model",
            "_manual_max_retries": 1,
            "_retry_delay_seconds": 0,
            "_retry_max_wait_seconds": 0,
        },
        "system",
        "user",
        0.1,
        stage="测试阶段",
    )
    assert result == {"ok": True}
    assert completions.calls == 2


def test_quality_contract_passes_and_catches_regressions():
    distilled, research = sample()
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert audit["publishable"], audit
    assert 500 <= audit["metrics"]["body_char_count"] <= 800

    invalid, research = sample()
    invalid["sections"] = [{"title": "不该出现"}]
    invalid["one_pager"]["key_sections"][0]["content"] += "本次处理了 42 个样本。"
    invalid["one_pager"]["references"].append({"title": "编造来源", "url": "https://invalid.example/report"})
    audit = audit_distilled(invalid, research, ("onepager",), strict_editorial=True)
    assert not audit["publishable"]
    assert "sections" in audit["metrics"]["forbidden_output_fields"]
    assert "42个" in audit["metrics"]["unsupported_numbers"]
    assert "https://invalid.example/report" in audit["metrics"]["invalid_reference_urls"]

    invalid_visual, research = sample()
    invalid_visual["one_pager"]["key_sections"][0]["visual_relation"] = "decorative"
    invalid_visual["one_pager"]["key_sections"][1]["visual_items"] = []
    audit = audit_distilled(invalid_visual, research, ("onepager",), strict_editorial=True)
    assert not audit["publishable"]
    assert audit["metrics"]["invalid_visual_relations"] == [1]
    assert audit["metrics"]["invalid_visual_items"][0]["section"] == 2


def test_short_article_requires_an_explicit_gap():
    distilled, research = sample()
    research["claims"][1]["importance"] = "medium"
    for section in distilled["one_pager"]["key_sections"]:
        section["content"] = section["content"][:70]
    distilled["content_gap"] = "缺少实验细节和独立复测。"
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert audit["publishable"], audit
    assert audit["metrics"]["body_char_count"] >= 250
    distilled["content_gap"] = ""
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert not audit["publishable"]


def test_bound_anchor_confirmation_fixes_paraphrase_without_waiving_anchors():
    distilled, research = sample()
    research["claims"][2]["claim"] = (
        "SPIRAL 论文报告，其方法在 8 个推理基准、4 个模型上最高带来 10% 的性能提升。"
    )
    boundary = distilled["one_pager"]["key_sections"][2]
    boundary["content"] += (
        "SPIRAL 论文摘要声称，其方法在 8 个推理基准、4 个模型上最高带来 10% 的性能提升；"
        "这是论文作者自报结果，不能替代独立复测。"
    )
    distilled["fact_check"][0]["note"] += (
        "SPIRAL 论文摘要写明覆盖 8 个推理基准和 4 个模型，最高提升 10%。"
    )
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert audit["publishable"], audit
    assert audit["metrics"]["raw_semantically_missing_high_claim_ids"] == ["c3"]
    assert audit["metrics"]["bound_anchor_confirmed_claim_ids"] == ["c3"]
    assert audit["metrics"]["semantically_missing_high_claim_ids"] == []

    boundary["content"] = boundary["content"].replace("最高带来 10%", "存在")
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert not audit["publishable"]
    assert audit["metrics"]["bound_anchor_confirmed_claim_ids"] == []
    assert audit["metrics"]["semantically_missing_high_claim_ids"] == ["c3"]


def test_metric_and_matrix_contracts_and_rendering():
    distilled, research = sample()
    first, second = distilled["one_pager"]["key_sections"][:2]
    first["visual_relation"] = "metrics"
    first["visual_items"] = [
        {"label": "准备", "value": "分步记录", "detail": "输入与人工条件分开"},
        {"label": "执行", "value": "保留失败", "detail": "不只展示理想结果"},
        {"label": "复核", "value": "可供复测", "detail": "复现条件能够回查"},
    ]
    second["visual_relation"] = "matrix"
    second["visual_columns"] = ["旧做法", "新流程"]
    second["visual_items"] = [
        {"label": "执行条件", "values": ["混合记录", "分步记录"], "detail": "条件可见性"},
        {"label": "失败结果", "values": ["容易省略", "明确保留"], "detail": "结果完整性"},
        {"label": "后续复测", "values": ["难以复现", "条件可回查"], "detail": "复测基础"},
    ]
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert audit["publishable"], audit

    article = SimpleNamespace(
        title="来源文章", author="作者", date="2026-08-25",
        retrieved_at="2026-08-25T00:00:00+08:00", url="https://example.com/research",
    )
    page = render_html(article, distilled)
    markdown = render_markdown(article, distilled)
    for text in ("relation-metrics", "metric-value", "relation-matrix", "data-label=\"旧做法\""):
        assert text in page
    assert "**关键数字**" in markdown
    assert "| 评测 | 旧做法 | 新流程 |" in markdown

    first["visual_items"][0]["value"] = ""
    second["visual_items"][0]["values"] = ["列数不匹配"]
    audit = audit_distilled(distilled, research, ("onepager",), strict_editorial=True)
    assert not audit["publishable"]
    assert {item["section"] for item in audit["metrics"]["invalid_visual_items"]} == {1, 2}


def test_renderers_are_semantically_aligned_and_escape_html():
    distilled, _ = sample()
    distilled["one_pager"]["key_sections"][0]["content"] += "\n\n<script>alert(1)</script> **关键边界**"
    article = SimpleNamespace(
        title="来源文章", author="作者", date="2026-08-25",
        retrieved_at="2026-08-25T00:00:00+08:00", url="https://example.com/research",
    )
    page = render_html(article, distilled)
    markdown = render_markdown(article, distilled)
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert "<strong>关键边界</strong>" in page
    for text in ("评测过程终于能被追溯", "来源", "分步追溯", "发布方结果"):
        assert text in page and text in markdown
    assert "一套新的评测流程把准备、执行和复核拆开记录" not in page
    assert "一套新的评测流程把准备、执行和复核拆开记录" not in markdown
    assert "<p class=\"lead\">" not in page
    for internal_text in ("资料与边界", "材料由研究团队发布", "只能确认发布方材料"):
        assert internal_text not in page and internal_text not in markdown
    for metadata in ("2026-08-25", "作者", "抓取于"):
        assert metadata not in page and metadata not in markdown
    assert 'data-layout="narrative-spine"' in page
    assert page.count('class="story-section') == 3
    assert 'class="relation relation-transition"' in page
    assert 'class="relation relation-loop"' in page
    assert 'class="relation relation-bottleneck"' in page
    assert "--accent:#5b9bd5" in page
    assert "--hero:#fff" in page
    assert '[data-theme="dark"]' in page
    assert '[data-theme="sepia"]' in page
    assert "theme-switcher" in page
    assert "setTheme('sepia')" in page
    assert "ad-theme" in page
    assert ".hero{position:relative;padding:54px 56px 44px;background:var(--hero)}" in page
    assert ".topics{margin:0 0 18px;color:var(--blue)" in page
    assert ".lead{max-width:620px;margin:24px 0 0;font-size:19px;line-height:1.7;font-weight:520;color:var(--muted)}" in page
    assert "--hero:#edf7f5" not in page
    assert "hero-rail" in page
    assert "linear-gradient" not in page
    assert "@media(max-width:480px)" in page
    assert 'href="https://example.com/research"' not in page
    assert "https://example.com/research" not in page
    assert "https://example.com/research" not in markdown
    assert "原始研究" in page and "原始研究" in markdown
    assert "<h2>来源</h2>" in page
    assert "## 来源" in markdown
    assert "**变化路径**" in markdown
    assert "1. **混合记录**" in markdown


def test_package_is_reproducible_and_contains_tests():
    with tempfile.TemporaryDirectory() as temp:
        first = package(Path(temp) / "first.zip")
        second = package(Path(temp) / "second.zip")
        assert first.read_bytes() == second.read_bytes()
        import zipfile
        with zipfile.ZipFile(first) as archive:
            names = set(archive.namelist())
        assert "article-onepager/tests/test_onepager.py" in names
        assert "article-onepager/scripts/onepager_mode.py" in names
        assert not any(name.startswith("article-onepager/.git/") for name in names)


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_")]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
