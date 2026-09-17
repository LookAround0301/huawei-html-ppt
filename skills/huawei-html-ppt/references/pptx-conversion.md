# HTML → 原生 PPTX 转换（两个分支通用）

触发条件：**用户明确要求**交付可编辑 PPT/PPTX 时才转换；默认交付物始终是 HTML
（可打印导出 PDF）。本规范适用于任何分支生成的 deck。

**禁止整页截图贴图**。必须重建为原生文本框/表格/形状（python-pptx），
"跟正常 PPT 一样可编辑"。

## 流程

1. `python-pptx`，`prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)`，
   空白版式 `prs.slide_layouts[6]`。
2. **数据从交付 HTML 解析**：按 `<!-- ==== 页名 ==== -->` 注释切块 →
   正则取 `<table>` 行列（`<br>`→`\n`、剥标签、`html.unescape`）→ 注入原生表格。
   HTML 是唯一数据源：改 HTML 后重跑脚本即可再出新 PPT，禁止手抄转录。
3. 表格：`add_table` + 逐格 `fill`（表头 `#F2F2F2` 粗体、正文白底）+ 逐格描边
   （XML `a:lnL/R/T/B`，0.5pt 近黑）；列宽按 HTML 的百分比换算 Emu。
4. 图形页（时间轴/流程/甘特/依赖图）用形状重建：矩形（轴/带/牌）+
   `MSO_SHAPE.ISOSCELES_TRIANGLE`（rotation 翻转方向）+ connector（`prstDash` 虚线）+
   `MSO_SHAPE.OVAL`；坐标函数**只做一次换算**返回英寸。
5. 页脚：`Page X/Y` 文本 + Huawei Confidential + logo 图片。
6. 每页构建后保存，用 **PowerPoint COM 导出 PNG 抽检**，迭代修到与 HTML 版一致：
   ```powershell
   $pp = New-Object -ComObject PowerPoint.Application
   $pres = $pp.Presentations.Open("$env:TEMP\out.pptx", $true, $false, $false)
   $pres.Slides.Item(3).Export("$env:TEMP\check.png", 'PNG', 1280, 720)
   ```

## 生成脚本模式

单文件脚本（如 `_build_pptx.py`）：解析函数 + 绘制 helpers
（tx / rect / tri / oval / conn / set_border / fill_cell / add_table /
footer / crumbs / title）+ 逐页构建函数。**脚本随工程保留，不要用完即删**——
HTML 内容变更后重跑即可再出新 PPT。

## 已踩过的坑（每条都实际翻过车）

- **rowspan 组列**：解析出的行会缺组单元格 → 补 `''` 占位到统一列数，
  再 `cell.merge()` 合并组列；**merge 会把被合并单元格的文本拼接进合并格**，
  所以只给左上角格填文本，其余留空。
- **fill_cell 必须 `tf.clear()` 再写**——否则对已填充单元格二次填充时
  同段落叠两个 run，出现"低时延低时延"叠字。
- **坐标只换算一次**：日期→英寸的函数返回结果不要再乘像素比例尺
  （二次换算会把所有标记挤到页面左缘）；距离阈值也统一成英寸再比较。
- 图片（logo/封面）按宽高比算宽度，右下角 logo 出界会被裁（logo 摆位留余量）。
- 字体：run 需同时设 `latin` 与 `a:ea`（东亚）typeface 为微软雅黑，否则中文回落宋体。
- 带色文本（蓝/红片段混排）用 run 级别着色；fill_cell 之后改 run 属性也可以。
- 长标题换行后注意与下方卡片标签（card-tab）的间距。
- 目标 PPTX 被用户开着时会 PermissionError——先落临时文件并验证，最后覆盖。
- 截图源（如需取页面元素位图）窗口宽必须 = 画布宽 1280，否则 html/body 的
  #555 背景被截进两侧，放进 PPT 成黑边。
- PowerPoint COM 打开中文路径会 E_FAIL——先把文件拷成 ASCII 路径名再导出。
