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
