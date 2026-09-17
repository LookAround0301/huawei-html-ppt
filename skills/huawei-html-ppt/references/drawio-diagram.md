# draw.io 画图（浏览器实时预览 + 嵌入 deck）

deck 需要架构图/流程图/拓扑图/时序图时用本流程。运行时已内置
（`tools/drawio-server/`，离线可用），来源 [next-ai-draw-io](https://github.com/DayuanJiang/next-ai-draw-io)。
架构：`Claude <stdio JSON-RPC> mcp-server <http> 浏览器(draw.io embed 实时预览)`。

## 1. 跑起来（按优先级）

1. **会话有 drawio 的 MCP 工具**（本 skill 以 plugin 安装时已随 `.mcp.json`
   自动注册，工具名形如 `mcp__plugin_huawei-html-ppt_drawio__*`；用户级
   注册 `~/.claude.json` 时为 `mcp__drawio__*`）：直接调 `start_session` /
   `create_new_diagram` / `edit_diagram` / `export_diagram`。
2. **无 MCP 工具**（注册晚于会话启动，最常见）：后台跑内置驱动脚本
   ```bash
   node ${CLAUDE_SKILL_DIR}/tools/drive_drawio.mjs 图.drawio    # 端口被占时前置 PORT=6003
   ```
   脚本：启动内置 server → initialize 握手 → start_session（自动开浏览器）
   → create_new_diagram（推送 XML）→ 挂住保活（server 死则预览断连）。
   改图：脚本只推一次，后续修改要么重启脚本，要么用 MCP 工具。
3. server 本体：`tools/drawio-server/dist/index.js`（tgz 解包 + npm install
   --omit=dev 后的完整运行时，勿动 node_modules）。

## 2. XML 要点（mxGraphModel）

```xml
<mxGraphModel pageWidth="1340" pageHeight="490">
  <root>
    <mxCell id="0"/><mxCell id="1" parent="0"/>
    <mxCell id="n1" value="文字（&#10;换行）"
            style="rounded=0;whiteSpace=wrap;html=1;fontSize=14;fillColor=#F2F2F2;strokeColor=#1D1D1A;"
            vertex="1" parent="1">
      <mxGeometry x="100" y="100" width="180" height="65" as="geometry"/>
    </mxCell>
    <mxCell id="e1" value="是" style="edgeStyle=orthogonalEdgeStyle;rounded=0;fontSize=13;
            exitX=0.5;exitY=0;entryX=0.5;entryY=1;" edge="1" parent="1"
            source="n1" target="n2">
      <mxGeometry relative="1" as="geometry"/>
    </mxCell>
  </root>
</mxGraphModel>
```

- 形状：矩形 `rounded=0` / 菱形 `rhombus;` / 椭圆 `ellipse;` / 便签 `text;`
- 连接点：`exitX/exitY`（起点）、`entryX/entryY`（终点），0~1 相对坐标
- 回边固定走线：`<Array as="points"><mxPoint x=".." y=".."/></Array>`
- 转义：`<`→`&lt;`、`>`→`&gt;`、换行 `&#10;`
- server 会 auto-fix 缺 mxfile 包裹等小问题；id 断链要自己保证
- create_new_diagram 是**整页替换**；改已有图用 edit_diagram（按 cell id）

## 3. 布局规范（给 deck 用的图）

- **横向版**：宽:高 ≈ 2.5~2.8:1（卡片区域 ~1170×420 的比例），主流程从左到右
  一条主线，分支节点放主线上/下侧，回边绕外圈+waypoints 固定。
- `fontSize ≥ 14`（嵌 deck 缩放 ~0.85x 后仍 ≥12px 可读）；便签/次要字 13。
- 节点间距 ≥60px 给边和 是/否 标签留位。
- 配色遵守本 skill 色卡：节点 `#F2F2F2` 灰 / `#FCE0E6` 红浅底（关键）/
  `#FDEED2` 琥珀浅底（注意）/ 白底黑边，回边 `#C00000` 虚线，边 `#1D1D1A`。

## 4. 嵌入 deck（关键路径）

**headless 导不出 PNG**（实跑结论，见下坑），标准路径是 **XML 坐标 → 等价内联 SVG**：

1. 按 draw.io XML 的 mxGeometry 值手写等价 SVG（rect/polygon/ellipse/polyline +
   marker 箭头 + text），配色字号照第 3 节；
2. 放进 `card`：`<svg viewBox="0 0 W H" style="width:100%;height:100%">`，
   外层 flex 居中，卡片 flex:1 撑满；
   **防裁边（实踩）**：卡片和内容容器都要加 `min-height:0`——
   `<div class="card" style="flex:1;...;min-height:0">` + 内层
   `style="...;flex:1;...;min-height:0"`。否则 flex 子项 `min-height:auto`
   不收缩，SVG 固有高度把卡片撑出 `.content-body`，底部被 `overflow:hidden`
   裁掉（症状：卡片底边框消失、图底部回边/输出节点缺一块）。
3. **坐标细节**：菱形=polygon 四顶点（上下左右尖）；边的折点即 polyline
   points；waypoints 直接抄；箭头 marker orient="auto"；
4. 多行文字用多个 `<text>`（y 递增 ~21px），`text-anchor="middle"` 居中；
5. 好处：自包含、缩放不糊、精确控色——这也与 style-guide"内联 SVG 天然
   自包含，优先于外链图片"一致。

交付物：`.drawio` 源文件（可编辑）+ deck 内嵌 SVG 版，两者内容一致。

## 5. 已知坑（实跑验证，别再踩）

- **headless Chrome 截不动预览页**：embed.diagrams.net 画布在 headless +
  `--virtual-time-budget` 下不渲染（截图只有工具栏，画布空白，且**视觉模型
  会幻觉"确认"图存在**——必须用像素检测交叉验证：非白像素计数）。
- viewer.diagrams.net 的 `data-mxgraph` div 在 file:// 下不初始化。
- kroki.io 渲染 API 国内 404。
- 端口固定 6002，占用时给进程设 `PORT` 环境变量。
- tgz 直接解包缺依赖（linkedom 等），本地跑要 `npm install --omit=dev`
  （内置运行时已装好，重装才需要）。
