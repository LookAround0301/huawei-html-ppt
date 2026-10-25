# Huawei HTML PPT

**把技术材料整理成有结论、图表清楚、可继续编辑的汇报。**

按用途选择「技术项目」或「洞察分析」风格，默认生成自包含 HTML 幻灯片。支持从源码和配置准备分析底稿，输出 SVG / draw.io 图源，并将实际反馈保存为可验证、可回退的规则。

[快速开始](#快速开始) · [怎么使用](#怎么使用) · [数据来源](#没有数据时怎么办) · [反馈迭代](#如何持续改进) · [详细使用说明](docs/usage.md)

## 可以做什么

| 场景 | 输入 | 输出重点 |
|---|---|---|
| 技术项目汇报 | 目标、方案、进展、评审材料 | 挑战与目标、目标与进展、专题布局、里程碑和交付判断 |
| 模型与特性洞察 | 报告、配置、代码、测试结果，或明确的模型版本 | 整体结构、局部变化、数据对比、实现约束和每页分析结论 |
| 昇腾适配分析 | 模型、硬件、精度、并行参数、实现版本 | A3/A5 等场景的量化、KV/状态、通信、P/D 并行与部署 |
| 参考材料学习 | AI 初版和人工修正终版 | 差异、适用规则、最小组件及回归案例 |

用户指定风格时优先遵从。否则按汇报目的选择，PCP/DCP 特性名称不会直接触发 PDCP 项目风格。数据已获用户确认时直接沿用。

## 快速开始

### 交给 Agent 安装

在支持本地 skills 的 Agent 中发送：

```text
请安装 https://github.com/LookAround0301/huawei-html-ppt 中的
skills/huawei-html-ppt，并查看 README 和 SKILL.md。
```

Agent 使用当前宿主的技能安装方式，保留已有修改；不要因安装而上传材料、安装全部分析仓库或配置远端服务。

### Claude Code 插件

```text
/plugin marketplace add LookAround0301/huawei-html-ppt
/plugin install huawei-html-ppt@huawei-html-ppt
```

可用 `/huawei-html-ppt` 或自然语言触发。更新时先更新 marketplace，再更新插件。仓库保留原插件名称与目录，不再自动注册旧 draw.io MCP 服务。

### Codex 本地技能

可让 Codex 从仓库安装 `skills/huawei-html-ppt`。手工安装先克隆：

```bash
git clone --depth 1 https://github.com/LookAround0301/huawei-html-ppt.git
```

将 `skills/huawei-html-ppt` 复制到当前环境的技能目录。以使用 `~/.codex/skills` 的本地环境为例，在仓库根目录执行：

```bash
python -c "from pathlib import Path; import shutil; shutil.copytree(Path('skills/huawei-html-ppt'), Path.home()/'.codex/skills/huawei-html-ppt')"
```

目标目录已存在时先备份或比较差异；该命令不会覆盖已有目录。新会话中使用 `$huawei-html-ppt`，或直接描述需求。

## 怎么使用

### 模型洞察

```text
用洞察分析风格制作这个模型的技术汇报，5页左右。
沿用附件中的基准数据，重点展示整体结构、相对上一版的局部变化，
以及 A3/A5 下的量化、KV Cache、并行策略和部署形态。
每页保留分析结论，来源放备注。所有材料仅在本地处理。
```

### 技术项目

```text
根据这些目标、方案和进展制作技术项目汇报。
单专题用“挑战＋目标”或“目标＋进展”；多个专题按技术布局和总进展组织。
标题说清内容，表格简洁，正文集中，不要无意义留白。
```

### 运行小例子

Python 3.10+ 即可运行 JSON 接口，不需要 Node 服务或大模型 API key。在仓库根目录执行：

```bash
python skills/huawei-html-ppt/scripts/ppt.py route examples/insight-request.json
python skills/huawei-html-ppt/scripts/ppt.py plan examples/insight-request.json
python skills/huawei-html-ppt/scripts/ppt.py render examples/insight-request.json local/insight
python skills/huawei-html-ppt/scripts/ppt.py render examples/project-request.json local/project
```

浏览器打开输出目录的 HTML。例子只有一页且使用明确标注的演示数据，不代表实际模型或硬件结果。JSON 接口负责路由辅助、读取规则、渲染和检查；技术分析及内容编写由宿主 Agent 完成。

## 没有数据时怎么办

先准备可追溯的底稿，再绘图排版：

| 来源 | 主要用途 |
|---|---|
| 模型发布方的 Hugging Face 仓库 | 配置、实际 forward、层型、维度、权重索引/元数据 |
| [se-tools](https://github.com/maoxx241/se-tools) | 参数、权重、缓存、通信及场景计算 |
| [model_analysis](https://gitcode.com/gcw_hasgjVbP/model_analysis) | 架构、算子与 Shape、DFG 和适配分析方法 |
| [vLLM-Ascend](https://github.com/vllm-project/vllm-ascend) | NPU 加载、量化、Attention、缓存、通信及 patch/覆盖实现 |
| [vLLM](https://github.com/vllm-project/vllm) | 匹配版本的上游调度、批处理、KV 管理、执行和并行分组 |

两个分析工具需要按模型适配，不只更换模型名套用旧公式。vLLM 与 vLLM-Ascend 匹配版本，并沿实际调用链判断实现归属。静态计算、场景估算和设备实测分开标记。默认只获取必要源码和元数据，不下载完整权重。

流程已写入 skill，由 Agent 按任务执行；目前没有把所有仓库封成一条全自动命令。

## 如何持续改进

以 **AI 初版＋人工终版** 作为学习样本：比较修改，提炼适用经验，再用相同内容重新生成并验证。写作偏好进入规则，稳定局部版式进入组件，绘图错误进入对应检查。

当前支持 `feedback → evaluate → review → promote` 和 `rollback`。候选有来源、适用范围和版本；验证前不影响正常生成，后续生成读取已采用的规则。

逐页匹配、视觉差异理解及代码修改由宿主 Agent 完成，并非后台自学习服务。新风格需要新增路由/布局并回归验证；单页变化优先复用现有分支。详见 [使用与反馈示例](docs/usage.md#反馈迭代)。

## 输出与边界

- 默认 1280×720 自包含 HTML，自动适应窗口，支持翻页和浏览器打印。
- 图形保留 SVG、draw.io 和结构化数据；文字使用黑灰红，少量低饱和填充。
- 洞察内容页保留显式“分析结论”；来源和制作批注放隐藏元数据/备注。
- 明确要求 PPTX 时按规范制作原生可编辑对象并验收；目前没有统一的一键 PPTX 转换命令。
- 原始材料、状态、测试输出和完整报告留在用户项目，不自动上传或发布经验。
- 已预留 [MindIE Agent 集成边界](skills/huawei-html-ppt/references/mindie-integration.md)，尚未接入其插件或知识服务。

## 目录与验证

```text
skills/huawei-html-ppt/
  SKILL.md             入口与风格选择
  references/          分支规范、分析方法、接口和演进说明
  assets/              页面样式、品牌资源、最小图形组件
  knowledge/           可版本化规则
  scripts/             路由、渲染、校验与反馈管理
examples/              两个单页接口例子
docs/usage.md          参数、反馈迭代和迁移说明
tests/                 不依赖私有材料的本地回归
```

```bash
python -m unittest discover -s tests -v
python skills/huawei-html-ppt/scripts/check_package.py
```

这些检查覆盖接口和基本结构。实际交付仍需逐页查看，核对数据、连接关系和可读性。
