# MindIE Agent 对接边界

参考公开仓库 `LookAround0301/mindie-agent` 的文档，固定版本
`a6d53de7ec164491be6f40666a189775afb3a552`：
[架构](https://github.com/LookAround0301/mindie-agent/blob/a6d53de7ec164491be6f40666a189775afb3a552/docs/architecture.md)、
[知识系统](https://github.com/LookAround0301/mindie-agent/blob/a6d53de7ec164491be6f40666a189775afb3a552/docs/knowledge-system.md)、
[演进设计](https://github.com/LookAround0301/mindie-agent/blob/a6d53de7ec164491be6f40666a189775afb3a552/docs/core-implementation-and-geak-evolution-design.md)。

该主仓当前主要是文档，不应把文档描述视为本地已安装的运行能力。

## 已实现

本模块提供本地 JSON CLI/API：route、plan、render、validate、catalog，以及反馈候选、评估、检查记录、采用和回退。
结构化规则有稳定 id、revision、范围和证据；每次 plan 读取当前规则，生成物记录所用版本。
不需要 Node 服务、远程模型调用或用户 MCP 配置。

## 未来宿主适配

| 宿主负责 | PPT 模块负责 |
|---|---|
| 用户会话、模型调用、理解材料、生成内容 | 确定性路由辅助、适用规则与组件查询 |
| 现有文件/浏览器/PowerPoint工具 | 本地HTML/SVG/draw.io及验证报告 |
| 语义评估、视觉检查、向用户交付 | 候选版本、检查证据和采用/回退 |
| 是否调用其知识服务 | 将PPT规则转换为适配器请求 |

宿主可将本地调用包装为 `ppt_plan`、`ppt_render`、`ppt_feedback` 等工具；这些名称是建议接口，**尚未注册到 MindIE Agent**。不要假设它现有知识服务接受本模块的 JSON 格式。

遵循其“宿主复用、确定性组件独立”的划分，不新建 Agent 循环或通用工作流引擎。映射知识服务时优先修订已有 id，保留 `id@revision` 和来源；只从 completed/verified-milestone 提炼，不把中间失败猜测提升为通用知识。

现阶段状态仅保存在调用者指定的项目目录；没有自动社区发布、云同步、后台学习或网络上传。未来集成仍须遵守用户对材料的权限要求。
