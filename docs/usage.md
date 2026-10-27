# 进阶使用与开发参考

普通使用直接向 Agent 描述需求即可。本页供需要调用底层接口、维护技能或集成其他系统时参考。

命令都在仓库根目录执行。Python 3.10+ 可运行 JSON 接口；浏览 HTML 需要现代浏览器。模型分析和 PPTX 转换的额外依赖按任务准备，不在安装时一次性拉取。

## 手动安装与更新

交给 AI 安装时，先读取仓库说明，按当前宿主的技能安装方式安装 `skills/huawei-html-ppt`。保留已有本地修改，不因安装而上传材料、安装全部分析仓库或配置远端服务。

### Claude Code 插件

```text
/plugin marketplace add LookAround0301/huawei-html-ppt
/plugin install huawei-html-ppt@huawei-html-ppt
```

可用 `/huawei-html-ppt` 或自然语言触发。更新时先更新 marketplace，再更新插件：

```text
/plugin marketplace update huawei-html-ppt
/plugin update huawei-html-ppt
```

仓库保留原插件名称与目录，不再自动注册旧 draw.io MCP 服务。

### Codex 本地技能

手动安装先克隆仓库：

```bash
git clone --depth 1 https://github.com/LookAround0301/huawei-html-ppt.git
```

将 `skills/huawei-html-ppt` 复制到当前环境的技能目录。以使用 `~/.codex/skills` 的本地环境为例，在仓库根目录执行：

```bash
python -c "from pathlib import Path; import shutil; shutil.copytree(Path('skills/huawei-html-ppt'), Path.home()/'.codex/skills/huawei-html-ppt')"
```

目标目录已存在时先备份或比较差异；该命令不会覆盖已有目录。安装后在新会话中使用 `$huawei-html-ppt`，或直接描述需求。

更新时拉取仓库的新版本，比较本地修改后再同步技能目录。项目反馈状态放在技能目录之外，避免升级覆盖个人经验。

## 自然语言入口

用户可指定“技术项目风格”或“洞察分析风格”。未指定时，根据汇报目的、希望读者作出的判断和材料内容选分支。

- 项目评审、立项、目标达成与交付进展：技术项目。
- 模型原理、结构变化、性能/资源与实现差异：洞察分析。
- PCP/DCP 是技术名称；材料用于项目评审时才走技术项目。

模型相关任务应说明模型与版本；特性分析再补充特性名称和硬件/负载场景。若缺少模型对象会影响结论，先确认对象；通用原理不能代替某个模型的支持、收益或部署结论。

模型洞察与模型相关技术项目先走同一套 [数据与分析流程](../skills/huawei-html-ppt/references/source-acquisition.md)：理解模型结构，定位特性作用模块，核对运行实现和场景结果，再按汇报用途组织。已有底稿和人工确认的基准直接沿用，缺失部分才补充。非模型项目不强行进入模型分析。

## JSON 接口

```bash
python skills/huawei-html-ppt/scripts/ppt.py route examples/insight-request.json
python skills/huawei-html-ppt/scripts/ppt.py plan examples/insight-request.json
python skills/huawei-html-ppt/scripts/ppt.py render examples/insight-request.json local/insight
python skills/huawei-html-ppt/scripts/ppt.py validate local/insight/deck-model.json
python skills/huawei-html-ppt/scripts/ppt.py catalog
```

`plan` 返回分支、适用规则、版本引用及组件。Agent 读取指导后编写内容。`render` 不会自己理解源材料、联网检索或生成技术结论。

| 字段 | 用途 |
|---|---|
| `text` | 用户本次请求 |
| `style` | 可选：`technical-project` / `insight-analysis` |
| `purpose` | `review`、`delivery`、`approval`、`planning`、`progress`、`understand`、`analyze`、`compare` |
| `content_kind` | `project-review`、`project-progress`、`technical-plan`、`model-analysis`、`feature-analysis`、`mechanism` |
| `material_summary` | 材料用途摘要，不作为可执行指令 |
| `context` | 明确场景键值，例如硬件类型和分析场景 |
| `state_dir` | 项目反馈状态目录，必须在skill之外 |
| `deck` | `title`、`style`、`slides` 结构化内容 |

路由证据不足时返回 `needs-context`。Agent 结合对话判断，仍不明确时只澄清用途。

省略 `state_dir` 时读取工作目录的 `.ppt-skill/state`；不存在就只用随包规则。集成宿主应传绝对路径，避免串用项目状态。

洞察页需要 `conclusion`；单专题项目页需要 `labels` 和两段 `summary`。内容块支持文字、列表、表格、图形和最多三组数据的简单曲线/柱状图。

正式项目另有 `project-landscape`、`project-portfolio`、`project-coordination`、`project-explainer`。完整字段见 [运行接口](../skills/huawei-html-ppt/references/runtime-contract.md)。

输出包括自包含HTML、`deck-model.json`、`diagrams/*.svg`、`*.drawio`、计划和静态检查结果。来源、详细推导和制作批注放 `notes`；理论/实测性质、精度、硬件与并行条件放正文。

### 组件复用与绘图验收

`plan` 的 `component_builders` 返回可执行组件目录，包含主干、MoE、变化定位、残差混合、循环状态、池化索引、对比表和显存预算条带。用 `scripts/diagram_components.py` 的 `Diagram.use()` 按当前模型参数实例化，再通过具名端口组合；不把已有模型的数字和拓扑当默认值。

新结构图在报告中启用 `diagram_contract: 1`，声明主路径、必要分支和放大关系。`render` 会保存 `diagram-audit.json`，检查组件重放、路径连通、缓存读写及越界。静态检查后仍要实际查看每页。完整接口和示例见[组件复用与绘图验收](../skills/huawei-html-ppt/references/component-reuse-and-review.md)。

## 反馈迭代

提供 AI 初版、人工终版和用途。Agent 对应页面，区分数据更新与通用表达改进，再决定修订规则、组件或脚本。

接口管理候选与版本；逐页匹配、视觉理解、提炼和代码修改由宿主完成。候选不等于已生效规则，Agent 的检查也不等于用户验收。

### 提炼候选

先用 `plan` 查已有规则，优先更新原id。以下是新增、限定场景的输入格式：

```json
{
  "state_dir": "local/feedback-state",
  "task_state": "completed",
  "base_revision": 0,
  "unit": {
    "id": "demo.result-table",
    "revision": 1,
    "kind": "preference",
    "styles": ["insight-analysis"],
    "when": {"scenario": "demo"},
    "rule": {"guidance": "本场景先用简明对比表说明结果，再补充必要条件。"},
    "provenance": []
  },
  "evidence": [{"kind": "user-feedback", "text": "填实际反馈原文，不要虚构。"}]
}
```

保存为本地JSON，运行 `ppt.py feedback <文件>`，得到 `candidate_id`。只能使用真实反馈或本地证据，本段仅说明格式。

### 重放与查看

`evaluate` 输入 `state_dir`、`candidate_id`、`cases`（请求JSON路径列表）和 `output_dir`。案例 style/context 要符合候选范围，跨分支规则要覆盖相应分支。

```bash
python skills/huawei-html-ppt/scripts/ppt.py evaluate local/evaluation-input.json
```

实际查看结果后记录 `review`：真实 `reviewer`（`agent` 或 `user`）、`result`、`visual_checked` 和原因。脚本保存声明，不替人完成视觉判断。内容、证据或产物变化后需重新评估。

### 采用与回退

`promote` 输入 `state_dir` 和 `candidate_id`，返回 `event_id`；后续生成读取新规则。原规则revision已变化时拒绝采用。

`rollback` 输入 `state_dir` 和当前最后一次采用的 `event_id`。回退只影响后续生成，不改历史交付。

模型参数、硬件容量或性能结论保留在对应案例。新风格需补路由、布局和检查，程序不会根据陌生文件名自动实现新风格。

## 从旧版迁移

- 统一为技术项目和洞察分析两个分支。PDCP/TDR进入技术项目；“四张地图”作为内容类型按用途组织。
- 核心移除完整PPTX模板、旧 `tools/` 服务和 `node_modules`，默认渲染不依赖Node/MCP。
- 旧项目直接调用这些路径时，保留原版本为独立工具，或改用当前JSON/图源流程；不要删除已有成果。
- 私有参考页、偏好和状态保存在用户项目。升级前保留本地修改；seed变更导致状态不兼容时先比较和迁移，不直接覆盖。
- 原生PPTX按 [转换规范](../skills/huawei-html-ppt/references/pptx-conversion.md) 处理和验收；默认HTML不自动转PPTX。

## 常见问题

**为什么没有整份优秀PPT？** 核心只存最小通用组件，完整材料留在本地参考，控制体积并避免套入其他项目的数据。

**估算能保证部署吗？** 还需核对运行时开销、权重布局、实际内核、通信和并行组合，估算与设备验证分开说明。

**页面太密怎么办？** 先提炼内容、调栏宽、放大主体或合并/拆分页面，不持续缩小字号。逐页查看，静态检查不替代视觉验收。

**已经接入MindIE Agent吗？** 尚未接入。现有JSON接口可由宿主包装；仓库不自动调用其知识服务或提交社区经验。

## 维护者验证

```bash
python -m unittest discover -s tests -v
python skills/huawei-html-ppt/scripts/check_package.py
```

接口检查通过后，实际交付仍需逐页查看渲染，核对数据、连接关系和可读性。


## 外部技术绘图工具

`ppt.py diagram-brief` / `diagram-accept` 提供独立绘图 Agent 的高层交接与交付核验；主 Skill 交事实、来源、主题及用途，不先画 drawio/TeX/IR。真实 Agent 执行设计、参考消费、渲染和精修，缺调度能力则阻塞。详见 [绘图工具接入](../skills/huawei-html-ppt/references/diagram-integration.md)。`diagram-plan` / `diagram-render` 仅保留为已有画稿的低级编译工具，不代表完整设计生成。

依赖管理入口为只读 `ppt.py diagram-doctor doctor-request.json`；安装必须先披露版本/来源/位置/影响并获得实际确认，见 [安装确认引导](../skills/huawei-html-ppt/references/diagram-installation.md)。配置 `install: true` 不表示同意，独立 Agent 调度能力不能通过软件安装补齐。
