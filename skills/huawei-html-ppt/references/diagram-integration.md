# 通过工具调用外部绘图 Skill

PPT 主 Skill 负责内容事实、来源、故事线、主题和展示约束；独立绘图 Agent 负责参考检索、语义设计、组件/UI、实际渲染、对照精修和交付。主 Skill 不先交画好的 drawio/TeX/IR。

高层 `diagram-brief` 准备独立 Agent 任务，`diagram-accept` 消费绘图交付；它们是交接协议，不是声称 Python 能自动模型推理。宿主通过真实 Agent 调度工具启动独立绘图执行者，并保存实际任务身份；没有该能力即阻塞。低级 `diagram-plan` / `diagram-render` 只处理作者已完成的画稿，保留调试用途，不能再作为完整绘图能力接入的完成证据。

调用前必须按 [只读预检与安装确认](diagram-installation.md) 检查依赖。高层 common 预检与后端预检分开；已满足就继续，缺失仅产安装方案并询问，不自动执行。

## 高层：内容委托给独立绘图 Agent

`diagram-brief request.json empty-output/` 的请求包含 `infra_root`（或环境变量）、`agent_dispatch_available` 与 `brief`。brief 的权威 schema 在独立绘图仓 `contracts/diagram-brief.schema.json`，包含 task_id、intent、question、audience、facts（事实 ID / 状态 / 来源）、target、theme、display_constraints、required_outputs、language_profile、preserve；不接收预制几何或画稿。theme 只交宿主颜色约束，不要求所有功能填充同灰。显示约束是可用空间/阅读要求，不是强制图比例。

外部 `tools/prepare_diagram_brief.py` 验证输入并生成 `brief.json` / `agent-task.md`。返回 `awaiting_drawing_agent` 只表示任务包准备好；没有调度能力则是 `blocked_no_agent_dispatch`，两者都不是生成完成。

宿主随后**实际调用独立 Agent 调度工具**，传入交接包及其 hash。Agent 读取独立绘图 Skill 和引用的完整工作流，从参考选择、语义建模、组件/字体/连接/比例设计，到实际渲染与参考对照修订；各阶段的引用、选项采用及对象映射按绘图仓交付契约记录。不得让主 Skill 预先写好 drawio/TeX 再只调用编译器冒充这一步。无 Agent 工具时停在明确阻塞，不虚构调度或临时用自身代替。

完成后保存实际 Agent 工具任务记录（不是一段“已执行”的自由文本），以及 dispatch JSON：

```json
{
  "mechanism": "independent_agent",
  "status": "completed",
  "host_agent_id": "actual-host-task-id",
  "drawing_agent_id": "actual-independent-task-id",
  "brief_sha256": "actual-sha256-of-prepared-brief",
  "task_record": "actual-agent-tool-record.json",
  "task_record_sha256": "actual-sha256-of-agent-tool-record"
}
```

这些是可审计执行记录，不是签名或自动证明记录真实；不能用测试 fixture 冒充实际执行。

`diagram-accept request.json empty-output/` 接受 `brief` / `delivery` / `dispatch` 本地路径、`artifact_root` 与必需的 `selected_variant_id`，调用独立仓 `tools/check_diagram_delivery.py` 校验真实引用文件与 hash、设计证据、selector 选项及绘图对象应用、渲染与视觉审查记录。生成 `accepted_contract_not_aesthetic_approval` 和可嵌入 `generated-diagram` block；主 Skill 不重新设计/编译此图。合同比对不等于自动美学、事实正确性或用户认可，独立 Agent 观察结论仍需如实保留。

交付失败/未成图、缺独立调度、未选/无效方案 ID、缺全部方案 PDF、变化的证据或不安全 SVG 均不嵌入。accept 只返回所选版的 blocks，同时返回所有方案目录及 `archive_pdf`（路径/hash）；换版只需明确另一个 ID 重新 accept，不需要重画。

可执行合成 brief 示例见仓库 `examples/diagram-brief-request.json`：

```sh
python skills/huawei-html-ppt/scripts/ppt.py diagram-brief examples/diagram-brief-request.json build/diagram-task
# 下一步必须由宿主实际 Agent 调度工具启动独立绘图 Agent，Python 命令不代替此步骤。
# Agent 完成后填写 accept 请求，再执行：
python skills/huawei-html-ppt/scripts/ppt.py diagram-accept selected-delivery.json build/accepted-diagram
```

accept 请求包含实际本地路径及 `selected_variant_id`，如 `{ "brief": "/project/task/handoff/brief.json", "delivery": "/project/drawing/diagram-delivery.json", "dispatch": "/project/task/dispatch.json", "artifact_root": "/project/drawing", "selected_variant_id": "V1" }`。选择 ID 必须来自实际交付，不假定一定叫 V1；示例不代表已有成图。已确认先图后解释：解释内容和篇幅由主 Skill 根据叙事决定；图内理解机制所需短标签/注释仍由绘图 Agent 完成。主 Skill 要主动把适宜的结果与结论图示化，但不把全部文字都改成图。

默认请求 3–4 个有统一编号、实质组织差异的方案。绘图 Agent 负责各版源图、真实渲染、视觉 QA 和包含全部编号方案的归档 PDF；主 Skill 在 accept 请求给 `selected_variant_id`，只嵌入所选版，并把归档 PDF 一并提供供人选择。此 PDF 是明确交付要求，不能被旧的“不默认给 PDF”偏好覆盖。只换色/圆角或重复图不算实质不同；合同检查不自动证明差异或美观。

主题色是大体协调的输入约束，允许绘图 Skill 采用自身朴素功能色，不因 RGB 不完全一致拒绝高层交付。主 Skill 可以按可用空间下单，但收到成图后再调整布局/反馈，图的自然比例优先。HTML 和实际 PPTX 必须使用同一所选产物等比、不裁切，并分别验收各格式；没有 PPTX 时只记录 HTML 检查，不能声称跨格式一致性已经验证。

主 Skill 最后仅检查图比例在页面中是否合适，必要时调整页面、放大或拆页，而不是要求绘图 Agent 为填满横屏把图重排为卡片。当前高层接口的合同测试不是新图质量恢复证明。

## 聚合与解耦边界

`scripts/diagram_adapter/` 是唯一绘图集成模块：Agent 交接、独立仓工具脚本、低级编译兼容、失败处理、证据校验和安全 SVG 嵌入均集中于此。绘图规则与后端仍在独立 `infra-io-generator` 仓库，不复制到 PPT 主干。

PPT 主入口只发现工具契约、分发高层 brief/accept 与低级 plan/render 请求；页面渲染器只传主题并消费 `generated-diagram` 返回结果，不了解具体 Skill 路径、图形 IR 或固定依赖提交。CLI JSON 与 block 契约为 adapter API 1，后续更换内部绘图实现保持此接口即可。

依赖升级只改模块内 `dependency-lock.json`，并同步安装固定提交；在更新前读外部变更，运行独立 adapter 测试、两分支真实导出、PPT 全回归与视觉验收，兼容性不满足则不升级。不在多个主干文件改版本，也不使用浮动 main。安装说明中的固定提交随 lock 同步。

```sh
python -m unittest discover -s tests -p test_diagram_adapter.py -v
python -m unittest discover -s tests -v
```

## 可选依赖与安装

核心 PPT 仍只用 Python 标准库，不联网安装、不复制大型 draw.io。只有新绘复杂技术图时需要 [infra-io-generator](https://github.com/grandolantow/infra-io-generator) 的两个同级 Skill。当前高层与低级接口固定公开 v0.10.5 提交：

```sh
git clone https://github.com/grandolantow/infra-io-generator.git /your/tools/infra-io-generator
git -C /your/tools/infra-io-generator checkout 19f1d210da9d5bcd3fca1eae656b50703d08ef9b
export INFRA_IO_ROOT=/your/tools/infra-io-generator
```

必须是完整、干净的固定 Git checkout（两个 Skill 及外部运行时），不只复制 SKILL.md。不自动下载执行依赖；更新 pin 必须审查与回归。源码保留在原仓库，不在此重新分发。依赖的许可与 draw.io notice 见原仓；部署者应检查其适用条件。

- 高层 prepare/check 合同工具：独立绘图仓声明的 Python `jsonschema` 依赖（按其依赖文件安装）；主 PPT 包不自动安装。
- report：Python 3.10+，调用原 `select_options.py` 和 `diagram_tool.py`。
- model 的默认 `drawio` 后端：额外需要 Node 20+、Playwright 和 Chromium；按依赖仓 [运行说明](https://github.com/grandolantow/infra-io-generator/blob/19f1d210da9d5bcd3fca1eae656b50703d08ef9b/docs/runtime.md) 安装。可在依赖 checkout 运行 `npm ci` 并安装 Playwright Chromium，或设置 `PLAYWRIGHT_MODULE` 指向已安装模块、`CHROME_BINARY` 指向浏览器。官方 Graph bundle 随依赖提供并在执行前核验 SHA256。
- model 的显式 `tikz` 后端：需要完整 TeX Live（XeLaTeX 或 pdfLaTeX、standalone、TikZ/PGF、所用字体包）以及 Poppler 的 `pdftocairo`。XeLaTeX 字体由作者声明并在运行环境安装；缺少格式/字体/宏包会明确失败。按外部仓运行说明配置受信的 TeX 资源，不自动安装或改变系统权限。
- 缺依赖、版本不符、无可用所选后端或检查失败时退出非零，不降级成“已调用”。

## 低级 API：已有画稿的调试与编译

以下接口不执行完整设计，不应要求主 Skill 在高层请求前准备这些输入。仅独立绘图作者/维护者可用于已完成画稿的执行与调试。

## 先按语义选工具

- `intent: model`：模型主干、层结构、Attention/MoE 模块连接。读取依赖的 `skills/technical-architecture-diagrams/SKILL.md` 及模型规范，著作未压缩 `.drawio` 和 cell/property 配色映射。执行专业原生 Graph 后端，不使用旧固定画布拓扑草稿 `render.py`。
- `intent: report`：通信、内存、调度、机制或定量解释。读取 `skills/technical-diagram-options/SKILL.md`、schemas/generation，著作 relational task JSON 和 diagram IR；selector 产生候选结构，Agent 选择后著作几何，generator 校验并导出 SVG/draw.io。
- 混合页：拆分两次调用，共享事实 ID 和术语。仅有模型名时先查来源，不按关键词瞎选。
- 原图适合时仍优先使用原图；普通图表/局部最小单元仍用原 PPT 组件。不能为证明调用而重画无必要原图。

```sh
python skills/huawei-html-ppt/scripts/ppt.py diagram-plan diagram-request.json
python skills/huawei-html-ppt/scripts/ppt.py diagram-render diagram-request.json output/new-diagram
```

请求示意（路径为本地文件，output 必须为空目录）：

```json
{
  "intent": "report",
  "request": "Explain memory mapping and address translation",
  "input": "/project/mapping.diagram.json",
  "task": "/project/mapping.task.json",
  "palette": "huawei-plain",
  "theme": {"accent":"#C00000","text":"#1D1D1A","muted":"#666666","background":"#FFFFFF","panel":"#F2F4F6","line":"#AEB8C0"}
}
```

model 支持可选 `page`（从 0 起，先抽出指定原生页再配色）；将 `input` 改为 `.drawio`，移除 `task`，补 `color_map`（本地 JSON 路径）及可选 `chrome`。色图格式沿用外部 Skill `apply_palette.py`：`{"cell-id":{"fillColor":"compute.fill","strokeColor":"compute.stroke","fontColor":"text.primary"}}`。给所有需要换色的图元声明映射，留白与文字不因颜色改变语义。只支持静态原生形状和纯文字，不加载外部图像、链接或 HTML 标签。

report IR 中 glyph 可选 `palette_role` 为 compute/state/communication/rank0/rank1/panel/accent/text；path 为 line/accent。缺省为 compute/line。适配器只替换样式，不改变事实、ID、位置和连接；最终 IR 一并保存。

## 布局偏好由绘图 Skill 提供

配置固定依赖后，`diagram-plan` 会真实读取独立绘图 Skill 的路由并展示 `layout_preferences`；未配置依赖时只返回 `requires_pinned_dependency`，不会凭 PPT 容器猜布局。模型当前倾向竖向主干加有解释价值的侧边展开，不是硬性竖排；技术图按任务选择结构。具体规则仍只在独立绘图仓维护，adapter 原样传递而不自动布图。

作者先看偏好并设计图，再适配页面，可提供 `layout_decision` 说明所选结构、偏离原因及实际视觉复核。render 将该作者记录和外部路由偏好保存到 invocation，`layout_review` 始终为 `not_automatically_evaluated`，不把作者陈述当自动验收。

升级依赖不会重画旧 HTML；旧 invocation 保留当时的 pin 和真实验证状态，不能改 SHA 冒充新版本。当前锁会拒绝将旧证据直接用于新 render，需明确重新执行才能得到新版本证据。

## 显式模型后端选择

`model_backend` 默认 `drawio`，按专业 Graph 后端运行。需要公式/论文原生 TeX 或用户明确选择时，可以显式 `model_backend: tikz`；不会因浏览器失败偷偷切换，也不使用旧拓扑草稿替代。

TikZ 请求仍提供相同原生 `input`/`color_map`，另给 `tex`、`tex_manifest`、`trusted_tex: true`，可选 `tex_engine: xelatex|pdflatex` 与 `tex_timeout`（1–180 秒）。适配器调用独立绘图仓的 `tools/render_model_tikz.py`，不在 PPT 主干编译或生成绘图源码。TeX 必须是当前任务作者已审阅的自包含源码，不默认信任下载内容；编译工具关闭 shell escape、使用隔离工作目录与受限文件读写，但不是任意恶意 TeX 的安全沙箱。

`tex_manifest` 必须绑定 `source_master_sha256`、`source_color_map_sha256`、`native_tex_sha256`、`language_profile`、`theme_tokens`、`palette`、`custom_tokens`、`page`，以及真实 `source_review: {reviewer: agent|user, result: pass, rationale: ...}`。它是作者核对标签、稳定 ID、端口与事实后的记录，不是编译自动证明语义等价。输入、主题或源码变化必须重新生成并核对，不允许给任意不同 TeX 配一张旧语言 QA。

SVG 的局部非递归 glyph 引用可以嵌入；外部资源仍被拒绝。保留 `.tex/.drawio/.pdf/.svg/.png` 及运行 QA，明确 TikZ 导出 SVG 中字形轮廓不可当作可编辑文字，编辑入口是 TeX 和结构母版。

## 低级兼容配色：既有 API 行为

以下保留旧编译接口以兼容已有画稿；高层委托不强制该同灰映射，绘图 Skill 按 theme 设计适度功能区分。

## PPT 默认朴素，主题亲和

两条分支都显式用 `huawei-plain`，不继承模型 Skill 的论文默认色。默认白底、黑灰文字、浅灰填充、少量红色强调。需要切换时显式 `palette: blue-neutral|paper-clear|paper-vivid`；即使切换，仍继承 PPT 主文字/底色/强调色，语义填充来自所选 palette。`custom_tokens` 可进一步覆盖外部 Skill 的嵌套语义 token，并校验对比度。

统一 `deck.theme` 和 diagram request 的六个 `theme` token。主页面 CSS 与图从同一组 token 解析；自定义色不能仅改图而不改页面。主题支持有效六位 HEX，不允许注入 CSS。外部 palette 的主文字对比度要求仍生效。颜色不改变布局；避免只靠颜色区分关系。

## 语言政策由绘图 Skill 统一维护

适配器默认透传 `language_profile: diagram-en-prose-zh` 给依赖仓共享的 `check_language.py`，不在 PPT 主干实现翻译或复制语言规则。图内短文本与可独立阅读长段说明的语义角色、例外和检查范围，以该绘图 Skill 的共享政策为准；著作时应读取政策并为可见文本标注 `text_role`，不能单凭框内外位置或字符数判断。

适配器对最终待渲染输入调用语言检查，绑定 QA 的 profile、输入 hash 和 QA 文件 hash。缺角色、未知角色或合同失败阻止生成；合同通过仍保留 `status: needs_review` 和 `semantic_review: not_run`，需要真实语义及视觉复核，不能把字符规则当全面语言认可。图周边的标题、分区、图例、箭头叙述、来源及限制说明均由绘图产物负责，不外包给 PPT 主干补写。

生成证据使用 invocation schema 2。旧产物没有该 QA，不可补一个标记就宣称符合新规则；必须修订图源后通过当前工具重新运行。已交付的旧 HTML 不会被自动修改。`language_qa` 是检查结果而非自动翻译，也不是用户认可。

## 真实调用与嵌入

成功结果包含 `blocks`，可直接放入 deck 的 `panels[].blocks`：

```json
{"type":"generated-diagram","path":"/project/output/artifacts/mapping.svg","invocation":"/project/output/invocation.json","alt":"Memory mapping and translation"}
```

PPT render 核对调用状态、固定依赖版本与 SVG hash，拒绝失败或修改过的产物；以自包含 SVG data URI 嵌入并保持比例。SVG 只接受静态内容，拒绝脚本、外部资源和 foreignObject。保留独立 SVG、draw.io、输入、配色、selector 结果及调用记录，不把 HTML 内图片称为原生 PPTX 对象。

`invocation.json` 记录实际执行的 Skill 脚本、返回码、输入和产物 hash。它证明此运行链路执行过，不证明事实正确、视觉优秀或用户认可，也不是防伪签名。日志与 `blocks.json` 可能含本地路径，属于用户项目产物，不能自动提交到公共仓库。核心不自动发布材料。

结构检查通过后仍需逐图和逐页渲染验收；不要将没有运行的 Inkscape、GUI 编辑或设备测试记为通过。CLI 缺失会明确失败，未调用不算成功使用 Skill。


页面可用 `deck.footer_label` 显式注明公开资料等用途；不提供时保持原有页脚默认。原生渲染 SVG/PNG 及其 QA 保留为 `model.native.*`，最终 `model.svg` 只对画布底色作主题适配并单独记 hash，不能把原生 PNG 当作已适配的最终图。
