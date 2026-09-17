---
name: article-onepager
description: 将网页文章、PDF 或 Word 文档压缩重组为 500-800 字、有来源边界的一页纸中文快讯，适用于简报、公众号短稿和快速决策阅读；不生成深度长文或小红书卡片。
---

# 文章一页纸

从原文中提取真正的信息增量，写成可连续阅读和分享的纵向一页纸。它不是长文摘要，也不是把深度文章机械截短，更不是分页幻灯片或卡片组。

本 Skill 自己拥有写作提示、输出结构、确定性质量门禁和 HTML/Markdown 渲染。共享 `article-distiller` 只提供网页抓取、来源登记、证据规范化、模型调用和发布壳层；集成边界见 [references/integration-contract.md](references/integration-contract.md)。

## 使用边界

- 需要完整论证、实验拆解或案例复盘：使用 `article-distiller`。
- 需要滑动阅读的 6-9 张知识卡：使用 `article-xhs-cards`。
- 需要 500-800 字快速判断稿：使用本 Skill。

## 执行

固定入口是 `scripts/run.py`，会强制加载 `scripts/onepager_mode.py`，不得直接调用共享引擎的旧 `onepager` 实现：

```bash
python <skill-root>/scripts/run.py <URL-or-local-file> -o <output-base>
```

输入可以是 URL、本地 `.txt`、`.md`、`.html`、`.pdf`、`.docx` 或 `.doc`；也可以使用 `--from-text` 显式指定文件。PDF 使用文字层提取，扫描 PDF 需先 OCR；`.doc` 需要 LibreOffice。支持共享引擎的 `--source-only`、`--render`、`--from-text`、`--official-url`、`--independent-url` 和 `--evidence-url` 参数，但不要传 `--format` 或 `--mode-adapter`。开始写作或验收时读取 [references/editorial-guide.md](references/editorial-guide.md)。

安装后先运行环境预检：

```bash
python <skill-root>/scripts/run.py --check
# 没有环境变量时，按实际配置文件检查
python <skill-root>/scripts/run.py --check --config /path/to/config.json
```

预检会自动寻找共享 `article-distiller`，检查 Python 版本、必要模块和 LLM 配置；缺项会显示当前解释器对应的可复制命令。共享引擎不在常见目录时，设置 `ARTICLE_DISTILLER_ROOT=/path/to/article-distiller`。只做抓取或渲染时可用 `python <skill-root>/scripts/check_environment.py --no-llm`，不要求 LLM key。

给他人分发时，先解压 `article-onepager.zip`，将其中的 `article-onepager/` 放入对方的 Skill 目录；安装边界、共享引擎位置和配置示例见 [references/installation.md](references/installation.md)。

默认性能策略由 `onepager_mode.py` 管理：研究阶段读取完整原文和最多 5 个已抓取来源，每份附件最多送入 6000 字；写作阶段只读取压缩证据账本与来源清单，不重复发送整篇原文。单次模型调用超时 180 秒，最多重试 1 次，并输出阶段耗时。草稿先通过本 Skill 的确定性门禁，只有失败时才调用模型做第三阶段审校；研究失败时回退到完整原文写作，不得用空账本生成。

## 内容要求

- 总正文控制在 500-800 字，使用 3-5 个带明确职责的论点式小节。
- 默认使用 `narrative-spine`：一个中心判断沿纵向论证轨道推进。关系、关键数字或多对象比较确实能压缩理解时，分别使用受控关系图、`metrics` 数字带或 `matrix` 比较矩阵。
- 导语用 1-2 句白话交代新变化和对读者的影响，不堆架构名、评测缩写或括号术语，不制造材料外悬念。
- 每个小节只承担 `fact`、`mechanism`、`impact` 或 `boundary` 中一个新信息单元，并用 `claim_ids` 绑定研究账本。
- 整页默认给非技术客户读，但使用官方简报口吻：清楚、克制、书面，不用口语。能用判断说清的，不要改写成评测说明书。
- 架构名、评测缩写、effort 档位、token 账单、oracle 路由、harness 和未对客户开放的内部细节，不进入成品正文。
- 读者成品不得出现来源处理口吻，例如“辅文称”“仓库称”“材料未核验”。
- 结尾回答“这对读者意味着什么”或“下一步应观察什么”，不重复导语。
- 引用只使用实际输入中的 URL；原文自证必须标为“原文声称”，独立核验必须对应已抓取材料。
- 不输出完整长文目录、实验卡组、思维导图、小红书发布文案或卡片 HTML。

视觉组件的字段、节点数量和移动端约束见 [references/editorial-guide.md](references/editorial-guide.md)。视觉节点只能压缩复述正文；`metrics` 和 `matrix` 中的每个数字也必须通过证据门禁，不得成为逃避核验的第二套文案。

## 交付

默认生成 HTML 和 Markdown。`source_bias_declaration`、`content_gap`、`source_notes`、抓取时间和其他运行元数据保留在结构化结果与审计中，不在读者成品里展示；首屏只放主题和标题；导语、来源审计和“尚无独立复测”等内部口径不进入读者成品。页脚只保留来源名称，不展示 URL。任务回报仍要说明哪些关键结论完成了独立核验，哪些只有原文证据；若材料不足以支持 500 字有效信息，宁可缩短并说明缺口，不得用背景常识凑字数。

维护时运行：

```bash
python <skill-root>/tests/test_onepager.py
python <skill-root>/scripts/package_skill.py -o /tmp/article-onepager.zip
```

修改共享适配接口后，还要运行共享项目的 `test_split_skills.py`。打包脚本会排除缓存和已有 ZIP，并验证关键文件是否齐全。

需要与深度解读和小红书卡片共同发布时，先独立完成并验收本 Skill 的 HTML/Markdown，再交给 `article-distiller/scripts/publish_shell.py` 组合。发布壳层不得回头改写一页纸内容。
