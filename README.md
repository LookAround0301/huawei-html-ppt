# huawei-html-ppt

生成华为官方模板风格技术汇报 PPT 的 Claude Code plugin：输出单文件自包含
HTML 幻灯片（1280×720，16:9，可打印导出 PDF），可按需转换**原生可编辑**
PPTX。内置三条业务分支（常规技术汇报 / PDCP·TDR 项目评审 / 团队"四张地图"）
与离线 draw.io 画图服务。

## 安装（Claude Code 会话内）

```
/plugin marketplace add LookAround0301/huawei-html-ppt
/plugin install huawei-html-ppt@huawei-html-ppt
```

或在终端执行等价的 `claude plugin marketplace add ...` / `claude plugin install ...`。

安装后直接说"帮我做一份华为风格的 XX 汇报 PPT"即可自动触发，
也可显式调用 `/huawei-html-ppt`。

更新：本 plugin 不固定版本号、按 git commit 自动版本化。仓库有更新时：

```
/plugin marketplace update huawei-html-ppt
/plugin update huawei-html-ppt
```

## 使用

安装后直接用自然语言描述任务即可自动触发（也可显式调用 `/huawei-html-ppt`）。
Skill 会按任务类型自动分流：

| 任务类型 | 你提供什么 | 得到什么 |
|---|---|---|
| **常规技术汇报** | 主题 / 大纲 / 单页内容 | 华为风格 HTML 幻灯片；明确要 PPTX 时转原生可编辑版 |
| **PDCP/TDR 项目评审** | xlsx 数据表 + 往期参考 PPT | 对照参考材料逐页制作的评审汇报（样式实抄参考，不自创） |
| **团队"四张地图"** | 团队信息（成员/岗位/氛围，口头描述或旧版 PPTX） | 业务/组织/人才/氛围地图：先 HTML 供验收，按需出原生 PPTX |
| **架构图/流程图/拓扑图** | 图的内容描述 | 浏览器实时预览迭代，交付 `.drawio` 源文件（deck 内嵌等价 SVG） |

触发示例：

- "帮我做一份华为风格的推理系统技术汇报 PPT，8 页左右"
- "对照这份往期 PDCP 材料和新版 xlsx，做本期的项目评审汇报"（附上文件）
- "给训练组做四张地图，PL 是张三，成员分工如下：…"
- "画一张大模型训练流程图，我要放进汇报里"

交付约定：

- **默认交付物是单文件自包含 HTML**（CSS 内联、图片 base64 内嵌），拷到任何
  机器都不丢资源；导出 PDF：Chrome 打开 → 打印 → 另存为 PDF。
- **只有明确要求 PPT/PPTX 时**才转换，且重建为原生可编辑对象
  （文本框/表格/形状），不做整页截图贴图。

## 在 Codex CLI 中使用

Skill 采用开放的 SKILL.md 格式（Agent Skills 规范），Claude Code 与
Codex CLI 通用。区别是 Codex 没有 plugin/marketplace 机制，需手动放置
skill 目录：

```bash
git clone https://github.com/LookAround0301/huawei-html-ppt.git
mkdir -p ~/.codex/skills
# 软链方式（推荐）：以后 git pull 即更新
ln -s /完整路径/huawei-html-ppt/skills/huawei-html-ppt ~/.codex/skills/huawei-html-ppt
# 或直接拷贝
cp -r /完整路径/huawei-html-ppt/skills/huawei-html-ppt ~/.codex/skills/
```

- **触发**：`$huawei-html-ppt` 显式提及，或自然语言描述任务（按 skill
  的 description 自动匹配）
- **项目级使用**：放到项目的 `.codex/skills/huawei-html-ppt/` 同样生效
- 文档中的 `${CLAUDE_SKILL_DIR}` 指 skill 根目录（即 SKILL.md 所在目录），
  在 Codex 中按实际放置路径理解即可

需要 draw.io 浏览器实时预览时，在 `~/.codex/config.toml` 注册 MCP server
（可选；不注册则走 skill 内置的 `tools/drive_drawio.mjs` 后备通道）：

```toml
[mcp_servers.drawio]
command = "node"
args = ["/完整路径/huawei-html-ppt/skills/huawei-html-ppt/tools/drawio-server/dist/index.js"]
```

## 依赖

- HTML 渲染/验收：Chrome 或 Chromium（headless 截图）
- 四张地图分支：Python 3 + pyyaml（HTML 路线）；再加 python-pptx（PPTX 路线）
- 四张地图 PPTX 的 COM 重排与 PNG 导出：Windows + PowerPoint + pywin32
  （不可用时自动降级并告警，HTML 路线不受影响）
- draw.io 实时预览：Node.js（server 运行时已内置本仓库，离线可用）

## 结构

- `skills/huawei-html-ppt/` — skill 本体：`SKILL.md` 入口与分流、
  `references/` 各分支规范、`assets/` 设计系统（huawei.css / 示例 / logo）、
  `tools/`（four-maps 生成器、drawio-server、驱动脚本）
- `.claude-plugin/` — plugin.json 与 marketplace.json（本仓库单插件兼任 marketplace）
- `.mcp.json` — 随 plugin 注册的 draw.io MCP server

## 本地开发

```bash
claude --plugin-dir ./     # 以本地目录加载测试（改动后 /reload-plugins 生效）
claude plugin validate ./  # 校验 plugin 结构
```
