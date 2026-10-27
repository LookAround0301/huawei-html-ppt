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

## 按需调用绘图工具

调用前按 [依赖预检与安装确认引导](references/diagram-installation.md) 执行只读 `diagram-doctor`：依赖齐则直接用，缺失先列明确方案并询问是否安装；只有真实确认后执行，再自检恢复原任务。配置字段不代表同意，调度能力不能通过安装补齐。

独立绘图仓库：[infra-io-generator](https://github.com/grandolantow/infra-io-generator)。它提供模型架构与技术机制/报告两类绘图能力，负责参考、设计、多方案渲染和视觉 QA；本 Skill 负责内容委托、选版与叙事排版。实际调用使用 `scripts/diagram_adapter/dependency-lock.json` 的固定提交，不直接执行浮动 main；安装与能力边界见 [绘图工具接入](references/diagram-integration.md)。

需要新绘模型架构或技术机制图时，主 Skill 只组织内容事实、来源、用途、主题与展示约束，先读 [绘图工具接入](references/diagram-integration.md)。高层入口 `diagram-brief` 生成独立绘图 Agent 交接包；宿主必须真正启动独立 Agent，令其从选参考、语义与组件设计到渲染、对照精修、验收完整执行绘图 Skill。主 Skill 不预先写 drawio、TeX、IR 或固定图形坐标。可以按可用空间下单，但给绘图 Agent 构图自主权；收到成图后再调整页面或反馈，不用页面横宽硬决定图构图。没有独立 Agent 调度能力时明确阻塞，不回退成主 Skill 先画好图后声称独立调用。

绘图 Agent 返回交付后，`diagram-accept` 核验独立工作流证据与产物，默认请求 3–4 个有统一编号、实质组织差异的方案，独立绘图 Agent 交全部方案源、视觉 QA 与统一归档 PDF。主 Skill 指定选择 ID，只将其中一版嵌入 HTML，保留全部方案 PDF 供用户选择；不能把换色或重复图当多个方案。先产图，再由主 Skill 决定解释内容与解释多少。主 Skill 要主动判断哪些结果与结论更适合图示，但不把所有文字机械画图。PPT 主题大体亲和即可，允许独立朴素功能色，不等于所有功能同灰；具体视觉设计由绘图 Skill 负责。按同一产物等比不裁切适配或拆页，HTML 与实际 PPTX 分别验收；未生成 PPTX 不声称两者已验证一致。`diagram-plan`/`diagram-render` 仅保留为已有画稿的低级规划/编译接口，不是完整设计生成入口，其调用次数不证明设计能力。原图与普通图表优先规则不变。

## 制作

1. 用 `plan` 读取本次分支、适用规则和最小组件；先理解材料的核心变化、实现约束和证据，再形成判断与组织页面。洞察结论按 [结论写法](references/insight-conclusions.md) 提炼关键事实、原因和具体判断，不能只摘抄数字或复述页题。已有结构化材料优先复用。
2. 技术项目先查用户材料、对应版本的仓库文档（含 `docs` 图片）和官方论文，有匹配原图就直接本地复用，不能默认重新画。先按 [原图复用规则](references/technical-project-style.md#原图优先) 核对版本与内容。下述内置最小组件规则只适用于主 Skill 自有的简单示意组件；独立模型架构/技术图走上面的 Agent 工具交接，不将这套实现要求重复施加给绘图 Agent。需要内置简单组件时再选组件：`assets/units/catalog.json` 是最小单元目录，`plan` 返回 `component_builders`；通过 `scripts/diagram_components.py` 实际实例化所需组件，保留参数、端口和使用记录，不能只在备注中写组件名称。新结构可扩展局部组件，不强套现有拓扑。见 [组件复用与绘图验收](references/component-reuse-and-review.md)。按问题选简单曲线、柱状图、对比表及必要的结构图，见 [chart-selection.md](references/chart-selection.md)。
3. 主 Skill 自有简单图继续沿用 [reference-diagram-fidelity.md](references/reference-diagram-fidelity.md)：完整主干、实际分支、缓存与回路，整体和局部放大明确对应；图内文字与批注黑灰红、低饱和填充，不能退化为无关联的方框卡片。直接使用的原图保留原貌，新增标注遵守黑灰红规范。
4. 用同一份 `deck-model.json` 生成 HTML，原图用 `image` 本地嵌入并保持比例；技术项目按图形密度选概览配表、图表核验或原图通栏，可点击放大。局部版式见 [技术项目风格](references/technical-project-style.md#原图和分析怎么搭配)。新绘图同步生成 SVG、draw.io，不把原图声称为可编辑图源。接口见 [runtime-contract.md](references/runtime-contract.md)。`python scripts/ppt.py render request.json output/`。逻辑画布1280×720，HTML自包含并自动适配。图表、说明和页数随内容变通，不强塞固定页数或重复卡片。
5. 主 Skill 自有简单结构图使用 `diagram_contract: 1`，在图中声明主路径、共享分支、缓存读写与放大对应关系；`validate` 校验真实组件重放和这些路径，`render` 保存 `diagram-audit.json`。原图检查来源、适用版本、清晰度、比例和关键内容完整性，不要求组件重放。再逐页检查字体、连线遮挡、留白、翻页及图的解释力。保存实际查看者和截图摘要；静态通过不能记成视觉通过或用户确认。
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
