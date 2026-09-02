# 安装与环境检查

## 安装边界

`article-onepager.zip` 是 Skill 包，不包含共享 `article-distiller` 引擎，也不包含任何 API key。安装者需要同时拥有：

- Python 3.10 或更高版本；
- `article-distiller` 共享引擎，推荐放在 `~/.workbuddy/skills/article-distiller`，也可以通过 `ARTICLE_DISTILLER_ROOT` 指定；
- `trafilatura`、`lxml-html-clean` 和 `openai`。读取 PDF 还需要 `pypdf`，读取 DOCX 还需要 `python-docx`；共享引擎启动时会尝试用当前 Python 自动安装缺失依赖，失败时按预检给出的命令安装；
- LLM 配置：`DISTILL_LLM_KEY`，或 `--config` 指向包含 `api_key` 的 JSON，或 ccswitch 当前启用的兼容提供商。`DISTILL_LLM_BASE_URL` 和 `DISTILL_LLM_MODEL` 可按提供商需要设置。

解压后，将 `article-onepager/` 放入目标 Skill 目录，然后运行：

```bash
PY=python3
SKILL=/path/to/article-onepager
$PY "$SKILL/scripts/run.py" --check
```

预检只显示缺项、路径和安装命令，不会显示 API key。若共享引擎不在默认位置：

```bash
ARTICLE_DISTILLER_ROOT=/path/to/article-distiller \
$PY "$SKILL/scripts/run.py" --check
```

预检会根据输入文件额外检查 PDF/Word 依赖：

```bash
$PY "$SKILL/scripts/check_environment.py" --no-llm --input report.pdf
$PY "$SKILL/scripts/check_environment.py" --no-llm --input report.docx
```

旧式 `.doc` 还需要系统 LibreOffice 的 `soffice` 命令；没有它时请安装 LibreOffice，或先另存为 `.docx`。

预检通过后才运行文章：

```bash
$PY "$SKILL/scripts/run.py" "https://example.com/article" -o /tmp/onepager
```

也可以直接把本地文件作为输入：

```bash
$PY "$SKILL/scripts/run.py" report.pdf -o /tmp/onepager
$PY "$SKILL/scripts/run.py" report.docx -o /tmp/onepager
$PY "$SKILL/scripts/run.py" report.doc -o /tmp/onepager
$PY "$SKILL/scripts/run.py" --from-text report.md -o /tmp/onepager
```

`--source-only` 和 `--render` 只需要抓取/渲染环境，不要求 LLM key：

```bash
$PY "$SKILL/scripts/check_environment.py" --no-llm
```

这个包适合在已有 `article-distiller` 的 Codex/本地 Python 环境中分发。若希望真正双击即用，需要另行制作包含共享引擎和 Python 运行时的安装器；当前 ZIP 不会复制或覆盖对方已有环境。
