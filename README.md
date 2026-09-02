# article-onepager

把网页文章、PDF 或 Word 文档压缩重组为 500–800 字、有来源边界的中文一页纸快讯。

## 使用

将 `article-onepager/` 放入 Codex 的 Skill 目录，然后运行：

```bash
python article-onepager/scripts/run.py <URL-or-local-file> -o <output-base>
```

支持 URL、`.txt`、`.md`、`.html`、`.pdf`、`.docx` 和 `.doc` 输入；PDF 使用文字层提取，扫描 PDF 需先 OCR，`.doc` 需要 LibreOffice。

## 依赖

- Python 3.10+
- 共享 `article-distiller` 引擎
- `trafilatura`、`lxml_html_clean`、`openai`
- 已配置的 LLM 提供商

安装后先运行环境检查：

```bash
python article-onepager/scripts/run.py --check
```

详细集成与安装边界见 `references/installation.md` 和 `references/integration-contract.md`。
