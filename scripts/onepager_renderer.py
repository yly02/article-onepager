"""Self-contained HTML and Markdown rendering for article-onepager."""

from __future__ import annotations

import html
import re
from typing import Any


def _text(value: Any) -> str:
    return str(value or "").strip()


def _esc(value: Any) -> str:
    return html.escape(_text(value), quote=True)


def _inline_html(value: Any) -> str:
    escaped = _esc(value)
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)


def _paragraphs(value: Any) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n|\n", _text(value)) if part.strip()]


RELATION_LABELS = {
    "contrast": "对照关系",
    "transition": "变化路径",
    "converge": "汇流关系",
    "bottleneck": "瓶颈转移",
    "loop": "闭环关系",
    "metrics": "关键数字",
    "matrix": "比较矩阵",
}


def _visual_items(section: dict) -> list[dict]:
    return [
        {
            "label": _text(item.get("label")),
            "detail": _text(item.get("detail")),
            "value": _text(item.get("value")),
            "values": [_text(value) for value in item.get("values") or []],
        }
        for item in section.get("visual_items") or []
        if isinstance(item, dict) and _text(item.get("label"))
    ]


def _visual_columns(section: dict) -> list[str]:
    return [_text(item) for item in section.get("visual_columns") or [] if _text(item)]


def _relation_html(section: dict) -> str:
    relation = _text(section.get("visual_relation"))
    items = _visual_items(section)
    if relation not in RELATION_LABELS or not items:
        return ""

    caption = f'<figcaption class="sr-only">{RELATION_LABELS[relation]}</figcaption>'
    if relation == "metrics" and 2 <= len(items) <= 4:
        cards = []
        for index, item in enumerate(items, start=1):
            detail = f'<p>{_inline_html(item["detail"])}</p>' if item["detail"] else ""
            cards.append(
                '<div class="metric-item">'
                f'<span class="metric-index">{index:02d}</span>'
                f'<strong class="metric-value">{_esc(item["value"])}</strong>'
                f'<span class="metric-label">{_esc(item["label"])}</span>{detail}</div>'
            )
        return (
            f'<figure class="relation relation-metrics">{caption}'
            f'<div class="metric-grid">{"".join(cards)}</div></figure>'
        )

    if relation == "matrix" and 2 <= len(items) <= 5:
        columns = _visual_columns(section)
        if not 2 <= len(columns) <= 4 or any(len(item["values"]) != len(columns) for item in items):
            return ""
        head = "".join(f'<th scope="col">{_esc(column)}</th>' for column in columns)
        rows = []
        for item in items:
            cells = "".join(
                f'<td data-label="{_esc(column)}">{_esc(value)}</td>'
                for column, value in zip(columns, item["values"])
            )
            detail = f'<span class="matrix-detail">{_inline_html(item["detail"])}</span>' if item["detail"] else ""
            rows.append(f'<tr><th scope="row">{_esc(item["label"])}{detail}</th>{cells}</tr>')
        return (
            f'<figure class="relation relation-matrix">{caption}<div class="matrix-scroll">'
            f'<table><thead><tr><th scope="col">评测</th>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div></figure>'
        )

    def node(item: dict, index: int, extra: str = "") -> str:
        detail = f'<p>{_inline_html(item["detail"])}</p>' if item["detail"] else ""
        return (
            f'<div class="relation-node {extra}" data-node="{index}">'
            f'<span class="node-index">{index:02d}</span>'
            f'<strong>{_esc(item["label"])}</strong>{detail}</div>'
        )

    if relation in {"contrast", "transition", "bottleneck"} and len(items) == 2:
        symbol = {"contrast": "↔", "transition": "→", "bottleneck": "›"}[relation]
        content = (
            f'{node(items[0], 1)}'
            f'<span class="relation-connector" aria-hidden="true">{symbol}</span>'
            f'{node(items[1], 2)}'
        )
    elif relation == "converge" and len(items) == 3:
        content = (
            f'<div class="converge-sources">{node(items[0], 1)}{node(items[1], 2)}</div>'
            '<span class="converge-connector" aria-hidden="true">↓</span>'
            f'{node(items[2], 3, "converge-target")}'
        )
    elif relation == "loop" and 3 <= len(items) <= 4:
        content = '<div class="loop-nodes">' + "".join(
            node(item, index) for index, item in enumerate(items, start=1)
        ) + "</div>"
    else:
        return ""
    return f'<figure class="relation relation-{relation}">{caption}{content}</figure>'


def _references(article: Any, distilled: dict) -> list[dict]:
    op = distilled.get("one_pager") if isinstance(distilled.get("one_pager"), dict) else {}
    candidates = list(op.get("references") or [])
    result = []
    seen = set()
    for item in candidates:
        if not isinstance(item, dict):
            continue
        url = _text(item.get("url"))
        if not re.match(r"^https?://", url, re.I) or url in seen:
            continue
        seen.add(url)
        result.append({"title": _text(item.get("title")) or url, "url": url})
    return result


CSS = """
:root{--paper:#fff;--ink:#1a1a1a;--muted:#6b7280;--line:#e5e7eb;--wash:#fff;--hero:#fff;--orange:#d97706;--blue:#5b9bd5;--green:#16a34a;--amber:#d97706;--link:#5b9bd5;--accent:#5b9bd5;--accent-soft:#f3f4f6;--metric-primary:#1f9d68;--metric-primary-soft:#eaf7f1;--metric-baseline:#4f7fd8;--metric-baseline-soft:#eaf1fd}
[data-theme="dark"]{--paper:#1a1d24;--ink:#e5e7eb;--muted:#9ca3af;--line:#2d3038;--wash:#0f1115;--hero:#1a1d24;--orange:#fbbf24;--blue:#8dc1f3;--green:#4ade80;--amber:#fbbf24;--link:#8dc1f3;--accent:#8dc1f3;--accent-soft:#182738;--metric-primary:#52c991;--metric-primary-soft:#17352b;--metric-baseline:#82aaf1;--metric-baseline-soft:#1b2b47}
[data-theme="sepia"]{--paper:#fffdf5;--ink:#4a3b2a;--muted:#8b7d6b;--line:#ddd0b8;--wash:#f5f0e1;--hero:#fffdf5;--orange:#b8860b;--blue:#8b6914;--green:#5d7c1f;--amber:#b8860b;--link:#8b6914;--accent:#8b6914;--accent-soft:#f5edd0;--metric-primary:#3d8b62;--metric-primary-soft:#e9f1e5;--metric-baseline:#587caa;--metric-baseline-soft:#e7edf3}
*{box-sizing:border-box}html{background:var(--wash)}body{margin:0;background:var(--wash);color:var(--ink);font-family:"Avenir Next","Segoe UI","PingFang SC","Noto Sans SC","Microsoft YaHei",sans-serif;line-height:1.75;letter-spacing:0;transition:background .2s,color .2s}
.theme-switcher{position:fixed;top:16px;right:16px;display:flex;gap:6px;z-index:100}.theme-btn{width:28px;height:28px;border-radius:50%;border:1.5px solid var(--line);cursor:pointer;transition:transform .15s}.theme-btn:hover{transform:scale(1.1)}.theme-btn.active{border-color:var(--accent);border-width:2px}.theme-light{background:#fff}.theme-dark{background:#0f1115}.theme-sepia{background:#f5f0e1}
main{width:min(100%,760px);min-height:100vh;margin:0 auto;background:var(--paper);overflow:hidden}
.hero{position:relative;padding:54px 56px 44px;background:var(--hero)}
.hero-rail{position:absolute;left:0;right:0;bottom:0;height:8px;display:grid;grid-template-columns:25% 33% 42%}.hero-rail i:nth-child(1){background:var(--amber)}.hero-rail i:nth-child(2){background:var(--blue)}.hero-rail i:nth-child(3){background:var(--green)}
.topics{margin:0 0 18px;color:var(--blue);font-size:13px;font-weight:700}.topics span+span:before{content:" · ";color:var(--muted)}
h1{max-width:640px;margin:0;font-size:42px;line-height:1.16;font-weight:780;letter-spacing:0;overflow-wrap:anywhere}
.lead{max-width:620px;margin:24px 0 0;font-size:19px;line-height:1.7;font-weight:520;color:var(--muted)}
.story{position:relative;padding:48px 56px 24px}.story:before{content:"";position:absolute;left:78px;top:48px;bottom:40px;width:2px;background:var(--line)}
.story-section{--section-accent:var(--orange);position:relative;min-width:0;margin:0 0 48px;padding:0 0 42px 58px;border-bottom:1px solid var(--line)}
.story-section:nth-child(4n+2){--section-accent:var(--green)}.story-section:nth-child(4n+3){--section-accent:var(--blue)}.story-section:nth-child(4n+4){--section-accent:var(--amber)}
.story-section:last-child{margin-bottom:0;border-bottom:0}.spine-node{position:absolute;z-index:1;left:-2px;top:1px;width:48px;height:34px;display:grid;place-items:center;background:var(--paper);border:2px solid var(--section-accent);color:var(--section-accent);font-size:12px;font-weight:800}
h2{margin:0 0 14px;font-size:28px;line-height:1.28;font-weight:760;overflow-wrap:anywhere}.section-copy p{margin:0 0 12px;font-size:16px;line-height:1.8;color:var(--ink)}.section-copy strong{font-weight:780;color:var(--ink)}
.relation{margin:24px 0 0;min-width:0}.relation-node{position:relative;min-width:0;padding:16px 16px 15px;border:1px solid color-mix(in srgb,var(--section-accent) 45%,var(--line));border-radius:6px;background:var(--accent-soft)}.relation-node strong{display:block;padding-right:28px;font-size:15px;line-height:1.4;color:var(--ink)}.relation-node p{margin:7px 0 0;font-size:13.5px;line-height:1.55;color:var(--muted)}.node-index{position:absolute;right:12px;top:13px;color:var(--section-accent);font-size:12px;font-weight:800}
.relation-contrast,.relation-transition,.relation-bottleneck{display:grid;grid-template-columns:minmax(0,1fr) 42px minmax(0,1fr);align-items:stretch}.relation-connector{display:grid;place-items:center;color:var(--section-accent);font-size:24px;font-weight:800}.relation-bottleneck .relation-connector{font-size:34px}
.converge-sources{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.converge-connector{display:block;height:34px;text-align:center;color:var(--section-accent);font-size:22px;line-height:34px}.converge-target{max-width:72%;margin:0 auto;border-width:2px}
.loop-nodes{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;padding:16px;border:2px solid var(--section-accent);border-radius:6px}.loop-nodes .relation-node{background:var(--paper)}
.metric-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.metric-item{position:relative;min-width:0;min-height:126px;padding:18px 13px 14px;border:1px solid var(--line);border-top:4px solid var(--section-accent);border-radius:6px;background:var(--accent-soft)}.metric-index{position:absolute;right:10px;top:7px;color:var(--section-accent);font-size:12px;font-weight:800}.metric-value{display:block;margin-top:3px;color:var(--section-accent);font-size:27px;line-height:1.15;font-weight:800;overflow-wrap:anywhere}.metric-label{display:block;margin-top:7px;color:var(--ink);font-size:12px;line-height:1.35;font-weight:700;overflow-wrap:anywhere}.metric-item p{margin:7px 0 0;color:var(--muted);font-size:12px;line-height:1.45}
.matrix-scroll{width:100%;overflow-x:auto;border:1px solid var(--line);border-radius:6px}.relation-matrix table{width:100%;border-collapse:collapse;background:var(--paper);font-size:13px;line-height:1.4}.relation-matrix th,.relation-matrix td{padding:11px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:middle}.relation-matrix thead th{background:var(--accent-soft);color:var(--muted);font-size:12px;font-weight:750}.relation-matrix th:first-child{text-align:left}.relation-matrix tbody th{width:34%;color:var(--ink);font-weight:750}.relation-matrix tbody tr:last-child th,.relation-matrix tbody tr:last-child td{border-bottom:0}.relation-matrix tbody tr:nth-child(even){background:var(--accent-soft)}.matrix-detail{display:block;margin-top:3px;color:var(--muted);font-size:12px;font-weight:500}.relation-matrix td{font-variant-numeric:tabular-nums;font-weight:700}
.evidence-footer{padding:32px 56px 52px;background:var(--accent-soft);border-top:1px solid var(--line)}.evidence-footer h2{margin:0 0 10px;font-size:16px}
.references ol{margin:0;padding-left:22px}.references li{padding:7px 0;font-size:14px;color:var(--ink);font-weight:650}.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
@media(max-width:600px){.theme-switcher{position:static;justify-content:flex-end;margin:10px 12px 0}.hero{padding:38px 22px 34px}h1{font-size:32px;line-height:1.14}.lead{font-size:16px;line-height:1.72}.story{padding:38px 20px 10px}.story:before{left:37px;top:38px;bottom:28px}.story-section{margin-bottom:38px;padding:0 0 34px 40px}.spine-node{left:-2px;width:38px;height:30px;font-size:12px}h2{font-size:22px}.section-copy p{font-size:15px;line-height:1.75}.relation-node{padding:14px 12px}.relation-node strong{font-size:14px}.relation-node p{font-size:13px}.relation-contrast,.relation-transition,.relation-bottleneck{grid-template-columns:minmax(0,1fr) 28px minmax(0,1fr)}.relation-connector{font-size:19px}.converge-sources{gap:9px}.converge-target{max-width:88%}.loop-nodes{grid-template-columns:1fr;padding:10px}.metric-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.metric-item{min-height:116px}.metric-value{font-size:24px}.evidence-footer{padding:28px 22px 42px}}
@media(max-width:480px){.relation-contrast,.relation-transition,.relation-bottleneck{grid-template-columns:1fr}.relation-connector{height:30px;transform:rotate(90deg)}.converge-sources{grid-template-columns:1fr}.converge-target{max-width:100%}.relation-matrix thead{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.relation-matrix table,.relation-matrix tbody,.relation-matrix tr,.relation-matrix th,.relation-matrix td{display:block;width:100%}.relation-matrix tbody tr{padding:11px 12px;border-bottom:1px solid var(--line)}.relation-matrix tbody tr:last-child{border-bottom:0}.relation-matrix tbody th{padding:0 0 8px;border:0}.relation-matrix td{display:flex;justify-content:space-between;gap:14px;padding:6px 0;border:0;text-align:right}.relation-matrix td:before{content:attr(data-label);color:var(--muted);font-size:12px;font-weight:600;text-align:left}.matrix-detail{max-width:90%}}
"""


def render_html(article: Any, distilled: dict) -> str:
    op = distilled.get("one_pager") if isinstance(distilled.get("one_pager"), dict) else {}
    title = _text(distilled.get("distilled_title")) or _text(getattr(article, "title", "")) or "文章一页纸"
    sections = [item for item in op.get("key_sections") or [] if isinstance(item, dict)]
    tags = [_text(item) for item in distilled.get("category_tags") or [] if _text(item)][:5]
    topics_html = "".join(f"<span>{_esc(item)}</span>" for item in tags)
    section_html = []
    for index, section in enumerate(sections, start=1):
        subtitle = _text(section.get("subtitle"))
        body = "".join(f"<p>{_inline_html(part)}</p>" for part in _paragraphs(section.get("content")))
        relation = _text(section.get("visual_relation"))
        section_html.append(
            f'<section class="story-section role-{_esc(section.get("role"))} visual-{_esc(relation)}" '
            f'aria-labelledby="section-{index}"><span class="spine-node" aria-hidden="true">{index:02d}</span>'
            f'<div class="section-copy"><h2 id="section-{index}">{_esc(subtitle)}</h2>{body}</div>'
            f'{_relation_html(section)}</section>'
        )

    refs = _references(article, distilled)
    refs_html = ""
    if refs:
        items = "".join(
            f'<li>{_esc(item["title"])}</li>'
            for item in refs
        )
        refs_html = f'<nav class="references" aria-label="来源"><h2>来源</h2><ol>{items}</ol></nav>'

    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(title)}</title><style>{CSS}</style></head><body>
<div class="theme-switcher">
  <div class="theme-btn theme-light active" onclick="setTheme('light')" title="亮色"></div>
  <div class="theme-btn theme-dark" onclick="setTheme('dark')" title="暗色"></div>
  <div class="theme-btn theme-sepia" onclick="setTheme('sepia')" title="护眼"></div>
</div>
<main data-layout="narrative-spine">
<header class="hero">{f'<div class="topics">{topics_html}</div>' if topics_html else ''}<h1>{_esc(title)}</h1>
<div class="hero-rail" aria-hidden="true"><i></i><i></i><i></i></div></header>
<div class="story">{''.join(section_html)}</div>{f'<footer class="evidence-footer">{refs_html}</footer>' if refs_html else ''}
</main>
<script>
function setTheme(t){{
  document.body.setAttribute('data-theme',t);
  document.querySelectorAll('.theme-btn').forEach(b=>b.classList.remove('active'));
  var btn=document.querySelector('.theme-'+t);
  if(btn) btn.classList.add('active');
  try{{localStorage.setItem('ad-theme',t)}}catch(e){{}}
}}
(function(){{
  try{{
    var t=localStorage.getItem('ad-theme');
    if(t) setTheme(t);
  }}catch(e){{}}
}})();
</script>
</body></html>"""


def render_markdown(article: Any, distilled: dict) -> str:
    op = distilled.get("one_pager") if isinstance(distilled.get("one_pager"), dict) else {}
    title = _text(distilled.get("distilled_title")) or _text(getattr(article, "title", "")) or "文章一页纸"
    parts = [f"# {title}", ""]
    for section in op.get("key_sections") or []:
        if not isinstance(section, dict):
            continue
        subtitle = _text(section.get("subtitle"))
        content = _text(section.get("content"))
        if subtitle:
            parts.extend([f"## {subtitle}", ""])
        for paragraph in _paragraphs(content):
            parts.extend([paragraph, ""])
        relation = _text(section.get("visual_relation"))
        items = _visual_items(section)
        if relation in RELATION_LABELS and items:
            parts.extend([f"**{RELATION_LABELS[relation]}**", ""])
            if relation == "metrics":
                for item in items:
                    detail = f"：{item['detail']}" if item["detail"] else ""
                    parts.append(f"- **{item['label']}：{item['value']}**{detail}")
            elif relation == "matrix":
                columns = _visual_columns(section)
                if columns and all(len(item["values"]) == len(columns) for item in items):
                    parts.append("| 评测 | " + " | ".join(columns) + " |")
                    parts.append("| --- | " + " | ".join("---:" for _ in columns) + " |")
                    for item in items:
                        label = item["label"] + (f"（{item['detail']}）" if item["detail"] else "")
                        parts.append("| " + label + " | " + " | ".join(item["values"]) + " |")
            else:
                for index, item in enumerate(items, start=1):
                    detail = f"：{item['detail']}" if item["detail"] else ""
                    parts.append(f"{index}. **{item['label']}**{detail}")
            parts.append("")

    refs = _references(article, distilled)
    if refs:
        parts.extend(["---", "", "## 来源", ""])
        parts.extend(f'- {item["title"]}' for item in refs)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"
