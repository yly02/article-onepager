# 一页纸编辑规范

## 输出契约

只要求 `distilled_title`、`category_tags`、`source_bias_declaration`、`content_gap`、`one_pager`、`fact_check`、`source_notes` 和 `editorial_coverage`。不要为了兼容共享引擎生成 `sections`、`experiment_ledger`、`case_stories` 或 `card_deck`。

`one_pager` 包含：

- `layout`：固定为 `narrative-spine`，表示从中心判断沿纵向轨道推进的连续长页。
- `lead`：2-3 句，先给变化、反差和影响；`lead_claim_ids` 绑定证据账本。
- `key_sections`：3-5 节，每节有 `role`、论点式 `subtitle`、短段 `content`、`claim_ids`、`visual_relation`、可选 `visual_columns` 和 `visual_items`。
- `references`：原文与实际抓取的证据链接，去重后列出。

`source_bias_declaration`、`content_gap`、`source_notes` 以及抓取时间等运行元数据是内部编辑与交付字段，供门禁、审计和任务回报使用，不渲染进面向读者的 HTML/Markdown。成品首屏只显示主题、标题和导语，页脚只保留 `references`。

`role` 只使用 `fact`、`mechanism`、`impact`、`boundary`。它是编辑和门禁字段，不在成品中显示。通常先给事实，再解释机制或影响，最后交代边界；材料不支持某种角色时不要硬凑。

`visual_relation` 使用 `none`、`contrast`、`transition`、`converge`、`bottleneck`、`loop`、`metrics` 或 `matrix`。视觉组件是正文的压缩表达，不是另一层内容：不得加入正文和证据中没有的新数字或新结论。

- `contrast`、`transition`、`bottleneck` 使用 2 个节点，`converge` 使用 3 个节点，`loop` 使用 3-4 个节点。
- `metrics` 使用 2-4 个项目，每项必须提供 `label` 和 `value`，只比较同一口径的关键数字。
- `matrix` 使用 2-4 个 `visual_columns` 和 2-5 行；每行提供 `label` 与等长 `values`，只用于多对象、多维度的同口径比较。
- 除 `matrix` 外不提供 `visual_columns`；没有清楚关系或高价值结构化数据时使用 `none` 和空数组。

## 编辑节奏

1. 导语回答“发生了什么，为什么现在值得看”。
2. 前半段给出最有信息量的事实或数字，同时保留样本与口径；存在 2-4 个同口径关键值时可使用 `metrics`。
3. 中段解释机制、原因或比较，不重复事实段。
4. 最后一节交代局限、尚未证实之处或读者下一步。

整页保持一条连续论证轨道。小节可以使用不同的视觉组件，但不能为了视觉变化拆散同一观点，也不能把每段文字包装成独立卡片。通常最多使用一个 `metrics` 和一个 `matrix`；关系、数字或比较不成立时宁可留白。

标题和小标题必须表达结论，避免“背景介绍”“核心内容”“总结”这类分类词。正文允许克制地加粗关键数字，但不使用卡片口吻、连续感叹或标题党表达。

## 来源门禁

- `cross_checked` 只能来自已成功抓取的独立来源。
- 只有原文时写“原文声称”，并保留作者、机构、样本和利益相关限制。
- 每个数字、日期、价格、性能比较和产品结论都必须能落到 `fact_check.evidence`。
- 不引用输入之外的 URL，不用常识补充成确定事实。
- 高优先级 claim 必须通过公开文案的语义覆盖检查。共享词法检查误判同义改写时，只有该 claim 已明确绑定到导语或小节、数字/版本/API 等强锚点全部出现、中文双字组召回达到门槛，且否定方向一致，才能由一页纸门禁确认覆盖；缺少任一条件仍阻止发布。

## 验收

- `body_char_count` 只统计导语和各节正文中的汉字，目标 500-800；少于 450 字通常信息不足，超过 900 字阻止发布。
- 材料确实不足时允许 250-449 字，但必须填写 `content_gap`，明确缺少的事实或证据。
- 有 3-5 个有效小节，无空节、占位符或高度重复内容。
- `layout` 为 `narrative-spine`，所有视觉类型、列和项目数量合法。
- 视觉节点与正文事实一致；节点中的数字同样通过事实证据门禁。
- `metrics` 的值口径一致；`matrix` 各行列含义清楚、值与列一一对应。
- 导语、中段和结尾承担不同功能。
- `editorial_coverage.covered_claim_ids` 与导语/小节公开使用的 claim ID 集合完全一致。
- 审计同时保留原始语义缺失、绑定锚点确认和最终有效缺失三个结果，不能用确认结果覆盖或删除原始诊断。
- 每个公开数字都能在 `fact_check` 的主张、说明、引文或 support 中找到同口径证据。
- HTML 与 Markdown 的事实、数字、链接和结论强度一致。
- HTML 与 Markdown 均不展示内部来源处理过程、抓取故障或审计说明；这些信息只保留在 JSON、审计和任务回报中。
