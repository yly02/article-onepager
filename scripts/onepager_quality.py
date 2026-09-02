"""Deterministic publication gate owned by article-onepager."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable

from editorial_quality import semantic_claim_coverage
from language_quality import find_language_issues


ALLOWED_ROLES = {"fact", "mechanism", "impact", "boundary"}
ALLOWED_LAYOUTS = {"narrative-spine"}
VISUAL_ITEM_COUNTS = {
    "none": {0},
    "contrast": {2},
    "transition": {2},
    "converge": {3},
    "bottleneck": {2},
    "loop": {3, 4},
    "metrics": {2, 3, 4},
    "matrix": {2, 3, 4, 5},
}
GENERIC_HEADINGS = {
    "背景介绍", "核心内容", "原因分析", "影响分析", "未来展望", "总结", "结论", "写在最后"
}
FORBIDDEN_OUTPUT_FIELDS = {
    "sections", "experiment_ledger", "case_stories", "card_deck", "quick_scan",
    "action_card", "takeaway_list", "visuals", "illustration_plan",
}
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)*(?:\s*(?:%|％|万|亿|元|美元|倍|年|月|日|个|项|次|小时|分钟|秒))?")
SENTENCE_RE = re.compile(r"[^。！？!?]+[。！？!?]?")
LATIN_ANCHOR_RE = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z][A-Za-z0-9]*(?:[-_.:/][A-Za-z0-9]+)*(?![A-Za-z0-9])"
)
NEGATION_RE = re.compile(r"(?:尚未|未能|未曾|未|没有|并无|无|缺少|不曾|不能)")
GENERIC_LATIN_ANCHORS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is",
    "it", "of", "on", "or", "that", "the", "this", "to", "up", "via", "with",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _claim_ids(value: Any) -> set[str]:
    return {_text(item) for item in _list(value) if _text(item)}


def _cjk_count(value: Any) -> int:
    return len(re.findall(r"[\u3400-\u9fff]", _text(value)))


def _normalized(value: Any) -> str:
    return re.sub(r"[^\w\u3400-\u9fff]", "", _text(value).lower())


def _duplicate_pairs(sections: list[dict]) -> list[dict]:
    duplicates = []
    for left in range(len(sections)):
        for right in range(left + 1, len(sections)):
            a = _normalized(sections[left].get("content"))
            b = _normalized(sections[right].get("content"))
            if min(len(a), len(b)) < 24:
                continue
            ratio = SequenceMatcher(None, a, b).ratio()
            if ratio >= 0.72:
                duplicates.append({"left": left + 1, "right": right + 1, "ratio": round(ratio, 3)})
    return duplicates


def _numeric_tokens(value: Any) -> set[str]:
    return {
        re.sub(r"\s+", "", match.group(0).replace(",", ""))
        for match in NUMBER_RE.finditer(_text(value))
    }


def _fact_corpus(distilled: dict) -> str:
    parts = []
    for check in _list(distilled.get("fact_check")):
        if not isinstance(check, dict):
            continue
        parts.extend([_text(check.get("claim")), _text(check.get("note"))])
        for evidence in _list(check.get("evidence")):
            if isinstance(evidence, dict):
                parts.extend([_text(evidence.get("quote")), _text(evidence.get("support"))])
    return "\n".join(parts).replace(",", "")


def _visual_items(section: dict) -> list[dict]:
    return [item for item in _list(section.get("visual_items")) if isinstance(item, dict)]


def _visual_copy(section: dict) -> str:
    parts = [_text(item) for item in _list(section.get("visual_columns"))]
    for item in _visual_items(section):
        parts.extend([
            _text(item.get("label")),
            _text(item.get("detail")),
            _text(item.get("value")),
            *[_text(value) for value in _list(item.get("values"))],
        ])
    return "\n".join(part for part in parts if part)


def _strong_anchors(value: Any) -> set[str]:
    """Return exact numeric, version, acronym, and API-name anchors."""
    anchors = {_normalized(token) for token in _numeric_tokens(value) if _normalized(token)}
    for match in LATIN_ANCHOR_RE.finditer(_text(value)):
        raw = match.group(0)
        lowered = raw.lower()
        if lowered in GENERIC_LATIN_ANCHORS:
            continue
        if (
            any(char.isdigit() for char in raw)
            or any(char in "-_.:/" for char in raw)
            or raw.isupper()
            or (len(raw) >= 3 and raw[0].isupper())
        ):
            anchors.add(_normalized(raw))
    return anchors


def _cjk_bigram_recall(claim: Any, corpus: Any) -> tuple[float, int]:
    def grams(value: Any) -> set[str]:
        result: set[str] = set()
        for run in re.findall(r"[\u3400-\u9fff]+", _text(value)):
            result.update(run[index:index + 2] for index in range(max(0, len(run) - 1)))
        return result

    claim_grams = grams(claim)
    corpus_grams = grams(corpus)
    if not claim_grams:
        return 0.0, 0
    return len(claim_grams & corpus_grams) / len(claim_grams), len(claim_grams)


def _bound_claim_corpora(op: dict, sections: list[dict]) -> dict[str, str]:
    """Build claim-specific public corpora from explicit lead/section bindings."""
    parts_by_id: dict[str, list[str]] = {}
    lead = _text(op.get("lead"))
    for claim_id in _claim_ids(op.get("lead_claim_ids")):
        parts_by_id.setdefault(claim_id, []).append(lead)
    for section in sections:
        public_section = "\n".join(filter(None, [
            _text(section.get("subtitle")),
            _text(section.get("content")),
            _visual_copy(section),
        ]))
        for claim_id in _claim_ids(section.get("claim_ids")):
            parts_by_id.setdefault(claim_id, []).append(public_section)
    return {claim_id: "\n".join(parts) for claim_id, parts in parts_by_id.items()}


def _confirm_bound_semantic_coverage(
    missing_ids: Iterable[str],
    claims: list[dict],
    op: dict,
    sections: list[dict],
) -> list[dict]:
    """Confirm conservative paraphrases that the shared n-gram gate can misclassify.

    A claim is confirmed only when it is explicitly bound to public copy, every strong
    anchor is present, Chinese bigram recall is high, and negative claims retain a
    negative cue. Claims without strong anchors are never overridden.
    """
    claims_by_id = {_text(item.get("id")): item for item in claims if _text(item.get("id"))}
    corpora = _bound_claim_corpora(op, sections)
    confirmed = []
    for claim_id in missing_ids:
        item = claims_by_id.get(claim_id) or {}
        claim = _text(item.get("claim") or item.get("text") or item.get("statement"))
        corpus = corpora.get(claim_id, "")
        anchors = _strong_anchors(claim)
        corpus_anchors = _strong_anchors(corpus)
        missing_anchors = sorted(anchors - corpus_anchors)
        recall, gram_count = _cjk_bigram_recall(claim, corpus)
        negation_aligned = not NEGATION_RE.search(claim) or bool(NEGATION_RE.search(corpus))
        if anchors and not missing_anchors and gram_count >= 6 and recall >= 0.55 and negation_aligned:
            confirmed.append({
                "claim_id": claim_id,
                "anchors": sorted(anchors),
                "cjk_bigram_recall": round(recall, 3),
                "bound_public_copy": True,
                "negation_aligned": negation_aligned,
            })
    return confirmed


def audit_distilled(
    distilled: dict,
    research: dict | None = None,
    required_modes: Iterable[str] = ("onepager",),
    strict_editorial: bool = True,
    semantic_coverage_strict: bool = True,
) -> dict:
    """Audit the one-pager contract without depending on shared mode rules."""
    blockers: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}
    if not isinstance(distilled, dict):
        return {"publishable": False, "score": 0, "blockers": ["一页纸顶层必须是对象"], "warnings": [], "metrics": {}}

    modes = {str(mode) for mode in required_modes}
    if modes != {"onepager"}:
        blockers.append(f"article-onepager 只接受 onepager 模式，收到：{sorted(modes)}")
    if not _text(distilled.get("distilled_title")):
        blockers.append("缺少 distilled_title")

    forbidden = sorted(FORBIDDEN_OUTPUT_FIELDS & set(distilled))
    metrics["forbidden_output_fields"] = forbidden
    if forbidden:
        blockers.append(f"一页纸包含其他输出模式字段：{forbidden}")

    op = distilled.get("one_pager") if isinstance(distilled.get("one_pager"), dict) else {}
    layout = _text(op.get("layout"))
    lead = _text(op.get("lead"))
    raw_sections = [item for item in _list(op.get("key_sections")) if isinstance(item, dict)]
    sections = [item for item in raw_sections if _text(item.get("subtitle")) and _text(item.get("content"))]
    body_chars = _cjk_count(lead) + sum(_cjk_count(item.get("content")) for item in sections)
    display_chars = body_chars + sum(_cjk_count(item.get("subtitle")) for item in sections)
    lead_sentences = [part.group(0) for part in SENTENCE_RE.finditer(lead) if _text(part.group(0))]
    duplicates = _duplicate_pairs(sections)
    invalid_roles = [index + 1 for index, item in enumerate(sections) if _text(item.get("role")) not in ALLOWED_ROLES]
    generic_headings = [index + 1 for index, item in enumerate(sections) if _text(item.get("subtitle")) in GENERIC_HEADINGS]
    invalid_visual_relations = []
    invalid_visual_items = []
    visualized_sections = []
    visual_char_count = 0
    for index, section in enumerate(sections, start=1):
        relation = _text(section.get("visual_relation"))
        items = _visual_items(section)
        raw_items = _list(section.get("visual_items"))
        columns = [_text(item) for item in _list(section.get("visual_columns")) if _text(item)]
        expected_counts = VISUAL_ITEM_COUNTS.get(relation)
        if expected_counts is None:
            invalid_visual_relations.append(index)
            continue
        if relation != "none":
            visualized_sections.append(index)
        invalid_nodes = [
            node_index + 1 for node_index, item in enumerate(items)
            if not _text(item.get("label"))
            or _cjk_count(item.get("label")) > 12
            or _cjk_count(item.get("detail")) > 36
            or (relation == "metrics" and not _text(item.get("value")))
            or (
                relation == "matrix"
                and (
                    len(_list(item.get("values"))) != len(columns)
                    or any(not _text(value) for value in _list(item.get("values")))
                )
            )
        ]
        invalid_columns = relation == "matrix" and (
            not 2 <= len(columns) <= 4
            or len(columns) != len(_list(section.get("visual_columns")))
            or len(set(columns)) != len(columns)
        )
        unexpected_columns = relation != "matrix" and bool(_list(section.get("visual_columns")))
        if (
            len(raw_items) != len(items)
            or len(items) not in expected_counts
            or invalid_nodes
            or invalid_columns
            or unexpected_columns
        ):
            invalid_visual_items.append({
                "section": index,
                "relation": relation,
                "item_count": len(items),
                "invalid_nodes": invalid_nodes,
                "column_count": len(columns),
                "invalid_columns": invalid_columns or unexpected_columns,
            })
        visual_char_count += _cjk_count(_visual_copy(section))
    metrics.update({
        "layout": layout,
        "section_count": len(sections),
        "body_char_count": body_chars,
        "display_char_count": display_chars,
        "visual_char_count": visual_char_count,
        "visualized_sections": visualized_sections,
        "lead_sentence_count": len(lead_sentences),
        "duplicate_sections": duplicates,
        "invalid_section_roles": invalid_roles,
        "generic_heading_sections": generic_headings,
        "invalid_visual_relations": invalid_visual_relations,
        "invalid_visual_items": invalid_visual_items,
    })

    if layout not in ALLOWED_LAYOUTS:
        blockers.append("一页纸 layout 必须为 narrative-spine")
    if not lead:
        blockers.append("一页纸缺少 lead")
    elif len(lead_sentences) not in {2, 3}:
        warnings.append(f"导语有 {len(lead_sentences)} 句，建议保持 2-3 句")
    if len(sections) < 3 or len(sections) > 5:
        blockers.append(f"一页纸有 {len(sections)} 个有效小节，必须为 3-5 个")
    if len(raw_sections) != len(sections):
        blockers.append("一页纸存在标题或正文为空的小节")
    if duplicates:
        blockers.append(f"一页纸存在高度重复小节：{duplicates}")
    if invalid_roles:
        blockers.append(f"一页纸小节缺少合法 role：{invalid_roles}")
    if generic_headings:
        blockers.append(f"一页纸使用空泛分类标题：{generic_headings}")
    if invalid_visual_relations:
        blockers.append(f"一页纸使用了无效 visual_relation：{invalid_visual_relations}")
    if invalid_visual_items:
        blockers.append(f"一页纸视觉节点与关系契约不一致：{invalid_visual_items}")

    content_gap = _text(distilled.get("content_gap"))
    if body_chars < 450:
        if strict_editorial and not (body_chars >= 250 and content_gap):
            blockers.append(f"一页纸正文只有 {body_chars} 字；材料不足时至少 250 字并填写 content_gap")
        else:
            warnings.append(f"一页纸正文只有 {body_chars} 字，已声明材料缺口")
    elif body_chars < 500:
        warnings.append(f"一页纸正文只有 {body_chars} 字，建议达到 500-800 字")
    if body_chars > 900:
        (blockers if strict_editorial else warnings).append(f"一页纸正文有 {body_chars} 字，超过硬上限 900 字")
    elif body_chars > 800:
        warnings.append(f"一页纸正文有 {body_chars} 字，建议压缩到 500-800 字")

    research = research if isinstance(research, dict) else {}
    claims = [item for item in _list(research.get("claims")) if isinstance(item, dict)]
    known_ids = {_text(item.get("id")) for item in claims if _text(item.get("id"))}
    high_ids = {
        _text(item.get("id")) for item in claims
        if _text(item.get("id")) and _text(item.get("importance")).lower() == "high"
    }
    public_ids = _claim_ids(op.get("lead_claim_ids"))
    missing_section_claim_ids = []
    for index, section in enumerate(sections, start=1):
        ids = _claim_ids(section.get("claim_ids"))
        if known_ids and not ids:
            missing_section_claim_ids.append(index)
        public_ids.update(ids)
    unknown_public_ids = sorted(public_ids - known_ids) if known_ids else []

    coverage = distilled.get("editorial_coverage") if isinstance(distilled.get("editorial_coverage"), dict) else {}
    covered_ids = _claim_ids(coverage.get("covered_claim_ids"))
    valid_omissions = [
        item for item in _list(coverage.get("omitted_claims"))
        if isinstance(item, dict) and _text(item.get("id") or item.get("claim_id")) and _text(item.get("reason"))
    ]
    omitted_ids = {_text(item.get("id") or item.get("claim_id")) for item in valid_omissions}
    missing_high_ids = sorted(high_ids - public_ids - omitted_ids)
    metrics.update({
        "public_claim_ids": sorted(public_ids),
        "covered_claim_ids": sorted(covered_ids),
        "missing_section_claim_ids": missing_section_claim_ids,
        "unknown_public_claim_ids": unknown_public_ids,
        "missing_high_priority_claim_ids": missing_high_ids,
    })
    if known_ids and covered_ids != public_ids:
        blockers.append("editorial_coverage.covered_claim_ids 与导语/小节实际 claim_ids 不一致")
    if missing_section_claim_ids:
        blockers.append(f"一页纸小节缺少 claim_ids：{missing_section_claim_ids}")
    if unknown_public_ids:
        blockers.append(f"一页纸引用了不存在的 research claim id：{unknown_public_ids}")
    if missing_high_ids:
        blockers.append(f"高优先级主张未公开覆盖且未说明舍弃原因：{missing_high_ids}")

    semantic = semantic_claim_coverage(distilled, research, ("onepager",))
    raw_semantic_missing = semantic.get("semantically_missing_high_claim_ids") or []
    bound_confirmations = _confirm_bound_semantic_coverage(
        raw_semantic_missing, claims, op, sections
    )
    confirmed_ids = {item["claim_id"] for item in bound_confirmations}
    semantic_missing = [claim_id for claim_id in raw_semantic_missing if claim_id not in confirmed_ids]
    semantic["bound_anchor_confirmations"] = bound_confirmations
    semantic["raw_semantically_missing_high_claim_ids"] = raw_semantic_missing
    semantic["semantically_missing_high_claim_ids"] = semantic_missing
    metrics["semantic_claim_coverage"] = semantic
    metrics["raw_semantically_missing_high_claim_ids"] = raw_semantic_missing
    metrics["bound_anchor_confirmed_claim_ids"] = sorted(confirmed_ids)
    metrics["semantically_missing_high_claim_ids"] = semantic_missing
    if semantic_missing:
        target = blockers if strict_editorial and semantic_coverage_strict else warnings
        target.append(f"高优先级主张未在公开文案中得到语义覆盖：{semantic_missing}")

    references = [item for item in _list(op.get("references")) if isinstance(item, dict)]
    reference_urls = [_text(item.get("url")) for item in references if _text(item.get("url"))]
    evidence_urls = set()
    unverified_evidence_urls = set()
    for check in _list(distilled.get("fact_check")):
        if not isinstance(check, dict):
            continue
        for evidence in _list(check.get("evidence")):
            if not isinstance(evidence, dict):
                continue
            url = _text(evidence.get("url"))
            if url:
                evidence_urls.add(url)
                if _text(evidence.get("source_type")).lower() == "unverified_link":
                    unverified_evidence_urls.add(url)
    invalid_reference_urls = sorted({
        url for url in reference_urls
        if not re.match(r"^https?://", url, re.I) or url not in evidence_urls
    })
    duplicate_reference_urls = sorted({url for url in reference_urls if reference_urls.count(url) > 1})
    metrics.update({
        "reference_urls": reference_urls,
        "invalid_reference_urls": invalid_reference_urls,
        "duplicate_reference_urls": duplicate_reference_urls,
        "unverified_evidence_urls": sorted(unverified_evidence_urls),
    })
    if invalid_reference_urls:
        blockers.append(f"参考链接未落到 fact_check.evidence：{invalid_reference_urls}")
    if duplicate_reference_urls:
        blockers.append(f"参考链接重复：{duplicate_reference_urls}")
    if unverified_evidence_urls:
        blockers.append(f"事实核查引用了未登记或未抓取的 URL：{sorted(unverified_evidence_urls)}")
    if not reference_urls:
        blockers.append("一页纸必须在长页内部保留至少一个参考链接")

    public_copy = "\n".join([
        lead,
        *[_text(item.get("content")) for item in sections],
        *[_visual_copy(item) for item in sections],
    ])
    public_numbers = _numeric_tokens(public_copy)
    fact_numbers = _numeric_tokens(_fact_corpus(distilled))
    unsupported_numbers = sorted(public_numbers - fact_numbers)
    metrics["public_numbers"] = sorted(public_numbers)
    metrics["fact_check_numbers"] = sorted(fact_numbers)
    metrics["unsupported_numbers"] = unsupported_numbers
    if unsupported_numbers:
        blockers.append(f"公开数字未落到 fact_check 证据说明：{unsupported_numbers}")

    language_issues = [
        issue for issue in find_language_issues({
            "distilled_title": distilled.get("distilled_title"),
            "one_pager": op,
            "source_bias_declaration": distilled.get("source_bias_declaration"),
            "content_gap": distilled.get("content_gap"),
        })
    ]
    metrics["language_issues"] = language_issues
    if language_issues:
        blockers.append(f"一页纸仍有 {len(language_issues)} 处高置信语言问题")

    score = max(0, 100 - 18 * len(blockers) - 4 * len(warnings))
    return {
        "publishable": not blockers,
        "score": score,
        "blockers": blockers,
        "warnings": warnings,
        "metrics": metrics,
    }


def choose_preferred(
    draft: dict,
    revised: dict,
    research: dict | None = None,
    required_modes: Iterable[str] = ("onepager",),
    strict_editorial: bool = True,
) -> tuple[dict, str, dict, dict]:
    draft_audit = audit_distilled(draft, research, required_modes, strict_editorial)
    revised_audit = audit_distilled(revised, research, required_modes, strict_editorial)
    draft_rank = (len(draft_audit["blockers"]), len(draft_audit["warnings"]), -draft_audit["score"])
    revised_rank = (len(revised_audit["blockers"]), len(revised_audit["warnings"]), -revised_audit["score"])
    if revised_rank <= draft_rank:
        return revised, "revised", draft_audit, revised_audit
    return draft, "draft", draft_audit, revised_audit


def assert_publishable(audit: dict, stage: str = "一页纸") -> None:
    blockers = list(audit.get("blockers") or [])
    if blockers:
        raise ValueError(f"{stage}未通过 article-onepager 门禁：" + "；".join(blockers[:8]))
