---
name: huawei-html-ppt
description: 制作和修改华为技术汇报 HTML/PPT，按用途自动选择技术项目或洞察分析风格，复用小型图表组件，并从实际反馈持续改进。
---

# 华为技术汇报

## 按用途进入两个分支

用户指定优先；未指定时综合汇报目的、读者要做的决定和材料内容判断。不能只看文件名或某个关键词。

| 分支 | 典型用途 | 页面表达 |
|---|---|---|
| 技术项目 `technical-project` | PDCP/TDR、立项、技术规划、目标和进展、交付评审 | 单专题：挑战＋目标或目标＋进展；多专题：专题目标＋节点＋技术布局/总进展 |
| 洞察分析 `insight-analysis` | 模型/特性原理、版本差异、性能和资源、硬件亲和性 | 每个内容页显式保留红色“分析结论”标签＋通栏浅灰结论块 |

PCP/DCP 是技术名称，不等于 PDCP。模型主题也能做项目评审；项目材料也能包含原理图。全篇用途决定主分支，具体页按问题选图表，不因局部内容切换分支。

`python scripts/ppt.py route request.json` 辅助判断，支持显式风格、目的及材料摘要。证据不足返回 `needs-context`；结合已有对话判断，只有仍影响选型时才询问用途。

- 技术项目：读 [technical-project-style.md](references/technical-project-style.md)。正式版布局提炼见 [project-report-reference.md](references/project-report-reference.md)。
- 洞察分析：读 [insight-analysis-style.md](references/insight-analysis-style.md)。需要计算时再读 [model-insight-workflow.md](references/model-insight-workflow.md)；用户确认的基准直接沿用。

## 制作

图内标题、节点、连线、图例和边注使用英文及标准术语，不出现中文；中文用于图外的页面标题、说明、分析结论和备注。绘图直接交付二维图像，布局按本次内容选择。

模型结构图优先基于匹配版本的 vLLM-Ascend 实际执行路径；继承部分继续查对应 vLLM。没有对应实现时，用 Hugging Face 源码或用户提供的结构/实现材料绘制，并说明原理与运行实现的边界。用户已确认的数据与版本约束继续沿用。图中体现关键融合算子和必要的 shape 变化，不套用其他模型的内核或维度。

1. 用 `plan` 读取本次分支、适用规则和最小组件；先理解材料的核心变化、实现约束和证据，再形成判断与组织页面。洞察结论按 [结论写法](references/insight-conclusions.md) 提炼关键事实、原因和具体判断，不能只摘抄数字或复述页题。已有结构化材料优先复用。
2. 技术项目先查用户材料、对应版本的仓库文档（含 `docs` 图片）和官方论文，有匹配原图就直接本地复用，不能默认重新画。先按 [原图复用规则](references/technical-project-style.md#原图优先) 核对版本与内容。需要新绘或改绘时再选组件：`assets/units/catalog.json` 是最小单元目录，`plan` 返回 `component_builders`；通过 `scripts/diagram_components.py` 实际实例化所需组件，保留参数、端口和使用记录，不能只在备注中写组件名称。新结构可扩展局部组件，不强套现有拓扑。见 [组件复用与绘图验收](references/component-reuse-and-review.md)。按问题选简单曲线、柱状图、对比表及必要的结构图，见 [chart-selection.md](references/chart-selection.md)。
3. 新绘图继续沿用 [reference-diagram-fidelity.md](references/reference-diagram-fidelity.md)，模型结构也可使用 [二维结构图组件](references/model-diagram-renderer.md)：完整主干、实际分支、缓存与回路。昇腾运行图先走读实际 Ascend 调用链，体现关键融合算子、启用条件及必要的 shape 变化，见 [执行实现与 shape](references/runtime-static-analysis.md#把实现画进模型结构)。图内文字与批注黑灰红、低饱和填充，不能退化为无关联的方框卡片。原图保留技术内容与拓扑，图内文字按英文规范处理；新增标注遵守黑灰红规范。
4. 用同一份 `deck-model.json` 生成 HTML，原图用 `image` 本地嵌入并保持比例；技术项目按图形密度选概览配表、图表核验或原图通栏，可点击放大。局部版式见 [技术项目风格](references/technical-project-style.md#原图和分析怎么搭配)。新绘图同步生成 SVG、draw.io，不把原图声称为可编辑图源。接口见 [runtime-contract.md](references/runtime-contract.md)。`python scripts/ppt.py render request.json output/`。逻辑画布1280×720，HTML自包含并自动适配。图表、说明和页数随内容变通，不强塞固定页数或重复卡片。
5. 使用 `diagram` 数据接口的新结构图设置 `diagram_contract: 1`，声明实际存在的主路径、共享分支与缓存读写；`validate` 校验组件重放和这些路径，`render` 保存 `diagram-audit.json`。使用二维 `Scene` 组件时单独保存场景、图源、`audit` 及源码语义核对记录，不将图片嵌入检查当作连线验收。原图检查来源、适用版本、清晰度、比例和关键内容完整性，不要求组件重放。再逐页检查字体、连线遮挡、留白、翻页及图的解释力。保存实际查看者和截图摘要；静态通过不能记成视觉通过或用户确认。
6. 明确需要可编辑 PPTX 时读 [pptx-conversion.md](references/pptx-conversion.md)，保留原生文字/表格/形状和备注，逐页渲染检查。默认交付 HTML。

共享要求见 [style-guide.md](references/style-guide.md)：大白话标题、准确术语、内容集中，减少大块无意义留白，不能靠小字和装饰填满。来源、依据、制作批注放隐藏元数据/演讲者备注；影响结论的条件正常显示。

模型洞察与涉及模型特性的技术项目，共用 [数据与分析流程](references/source-acquisition.md)：用户材料优先，从模型结构和匹配版本的运行实现出发，分析特性作用的模块、状态、通信及场景结果，再形成同一份底稿。按需使用官方模型仓库、se-tools / model_analysis、vLLM-Ascend 和上游 vLLM；不是每次都跑全部工具。调度和缓存路径按 [运行实现分析](references/runtime-static-analysis.md) 核对 patch/覆盖。两分支只改变汇报重点，不分别编造数据或支持结论；无模型关联的项目直接用项目材料。涉及A3/A5部署判断时按 [部署分析](references/ascend-deployment-analysis.md) 分别核对场景，不把个案容量当通用硬件参数。

本地材料不上传。解析与渲染在本机；不把私有内容送到外部绘图、图像生成、云文档或搜索服务。

## 从反馈改进

执行宿主负责分析和模型调用，本模块负责确定性生成、检查和本地规则版本管理。不运行后台自学习服务。

- 用户反馈或已验证案例形成候选规则；优先修订已有单元，注明适用范围与证据。
- `feedback → evaluate → review → promote` 后成为下次 `plan` 实际读取的规则；未通过的候选不进入正常生成。
- 视觉变更需要实际查看渲染结果；不能用脚本通过冒充人工认可。记录是谁做了检查，不能将 Agent 检查记成用户确认。
- 可以 `rollback` 回退。新案例不能默默改动已交付的 PPT 或扩大为全局规则。

接口与状态位置见 [runtime-contract.md](references/runtime-contract.md)，演进规则见 [evolution.md](references/evolution.md)。状态、测试产物和完整报告放在项目目录，核心包不携带 `node_modules`、整份PPT或实际项目数据。

未来对接 MindIE Agent 的边界见 [mindie-integration.md](references/mindie-integration.md)；目前提供本地 JSON 接口，尚未接入它的宿主插件或知识服务。
