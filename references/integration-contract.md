# 共享引擎集成契约

只在维护脚本、排查入口或打包时读取。

## 职责

共享 `article-distiller/scripts` 负责：

- 抓取原文、官方附件与独立来源。
- 建立来源登记和研究证据账本。
- 调用 OpenAI 兼容模型。
- 规范化证据等级、保守修复明确语言问题。
- 提供概念索引和发布壳等通用后处理。

`article-onepager` 负责：

- `onepager_prompt.py`：写作提示和编辑审校提示。
- `onepager_quality.py`：结构、篇幅、claim 覆盖、数字证据和语言门禁。
- `onepager_renderer.py`：HTML 与 Markdown 语义等价渲染。
- `onepager_mode.py`：向共享 CLI 暴露稳定接口。

## Adapter API

`onepager_mode.py` 必须导出：

```text
MODE = "onepager"
SYSTEM_PROMPT
EDITORIAL_REVIEW_PROMPT
audit_distilled(...)
choose_preferred(...)
assert_publishable(...)
render_html(article, distilled)
render_markdown(article, distilled)
```

Adapter 还可以声明一页纸专用的性能预算：模型超时与重试次数、送入研究阶段的附件数量和截断长度、研究账本长度、写作上下文模式，以及编辑审校策略。研究阶段仍允许读取最多 5 个来源，但单份正文限制为 6000 字；固定入口把每个 GitHub 仓库的深读文件限制为 3 个。写作只读取压缩后的研究账本，草稿通过确定性门禁时跳过第三次模型审校。用户显式传入的 CLI 数量参数优先于入口默认值。

固定入口将 adapter 的绝对路径传给共享 CLI。用户不能覆盖 `--format` 或 `--mode-adapter`。共享 CLI 在没有 adapter 时保持旧行为，以兼容历史项目；这不是本 Skill 的执行路径。

`scripts/check_environment.py` 负责安装后预检。它按 `ARTICLE_DISTILLER_ROOT`、当前 Skill 的兄弟目录和常见 Skill 目录寻找共享引擎，检查 Python 版本、抓取/LLM 模块和 LLM 配置，但不打印或保存 API key。固定入口在正常运行前自动执行同一检查；`--check` 只检查并返回结果。`--source-only` 与 `--render` 不要求 LLM 配置。

## 发布顺序

共享引擎完成抓取和研究后，将压缩证据账本、已抓取来源清单与本 Skill 的提示交给写作模型。草稿先运行本 Skill 门禁；通过时直接进入共享证据规范化，失败时才调用编辑审校模型。规范化后再次运行本 Skill 门禁，最后调用本 Skill 渲染器。任何一次门禁失败都不得输出半成品。

共享语义检查的原始结果必须保留。一页纸可以在自己的门禁中纠正已绑定公开段落的保守词法假阴性，但确认条件必须同时覆盖强锚点、中文语义召回和否定方向；不得改写共享算法或影响其他输出模式。审校稿只有在结构、数字证据和最终有效语义覆盖都优于草稿时才会被选择。
