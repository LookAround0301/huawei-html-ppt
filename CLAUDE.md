# 仓库维护约定

本仓库发布 `skills/huawei-html-ppt`，同时保留 Claude Code 插件/marketplace 元数据。面向用户的说明和技能内容使用中文。

## 结构

- `skills/huawei-html-ppt/SKILL.md` 按用途选择技术项目或洞察分析。
- `scripts/ppt.py` 提供本地 JSON 接口；核心只使用 Python 标准库。
- `references/` 渐进加载规范。`assets/units/` 只保留最小组件。
- `knowledge/units.json` 是随包规则；用户状态放项目外部目录，不写入安装包。
- `.claude-plugin/` 保持插件名、marketplace 名及 skill 目录一致。

## 修改与验证

```bash
python -m unittest discover -s tests -v
python skills/huawei-html-ppt/scripts/check_package.py
```

图形或布局变更还需生成 HTML 并逐页查看。检查通过不等于视觉验收通过。

内容与数值从结构化底稿生成，保持图、表、正文一致。洞察内容页保留分析结论，来源放隐藏元数据或备注，影响判断的条件正常显示。

## 发布边界

不提交私有报告、样例原件、个人路径、反馈状态、浏览器 profile、凭据或完整模型权重。只保留通用规则、局部组件和匿名化示例。

核心不再携带旧版 Node 绘图服务、node_modules 或完整PPTX模板，也不自动注册 MCP 服务。复杂原始图通过用户本地工具处理，保留可编辑源文件。

根目录 README 与 `docs/usage.md` 说明已实现能力，不把未来自动化或 MindIE 对接写成已完成。

插件元数据不固定 version，沿用仓库按提交更新的方式；若后续添加版本字段，发布时同步更新。规则与运行接口的兼容性另行检查。
