# HTML → 原生 PPTX 转换（两个分支通用）

触发条件：**用户明确要求**交付可编辑 PPT/PPTX 时才转换；默认交付物始终是 HTML
（可打印导出 PDF）。本规范适用于任何分支生成的 deck。

**禁止整页截图贴图**。必须重建为原生文本框/表格/形状（python-pptx），
"跟正常 PPT 一样可编辑"。

直接引用的文档/论文原图保留为独立图片对象，等比例完整放置；不得为追求可编辑把它重新画一遍。页面标题、正文、表格及新增覆盖标注仍为原生对象，图片来源和处理说明写入对应页备注。

## 流程

1. `python-pptx`，`prs.slide_width=Inches(13.333); prs.slide_height=Inches(7.5)`，
   空白版式 `prs.slide_layouts[6]`。
2. **同一份结构化数据**：优先读取交付 HTML 的 `script#deck-model` 或相邻 `deck-model.json`，从 slides、panels、blocks、diagram 和 notes 生成原生对象。旧版没有元数据的HTML再按其DOM解析；不要默认依赖不存在的分页注释，也不要手工转录数据。
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

## 单位换算铁律（最容易整页翻车的地方）

HTML 画布是 **1280×720 px @ 96 dpi**，CSS 字号/坐标都用 `px`。PPTX 的尺寸
单位是**英寸**，字号单位是**磅 pt**（1 pt = 1/72 inch）。两者换算系数不同，
**位置用 96、字号用 72，绝不能混用同一个系数**：

| 量 | HTML 单位 | PPTX 单位 | 换算 | 系数 |
|---|---|---|---|---|
| 位置/宽高 | px | Inches | `Inches(px/96)` | 96 |
| **字号** | **px** | **Pt** | **`Pt(px*72/96)` = `Pt(px*0.75)`** | **72** |
| 行间距/边距 | px(估) | Pt | `Pt(px*0.75)` | 72 |
| 线宽/边框 | px | Pt | 直接 Pt（视觉量，可不缩放） | — |

**核心坑**：把 CSS px 字号直接 `Pt(size)` 传入，会让**所有字号放大 1.333 倍**
（96/72），文字在按 HTML 较小 px 字号设计的文本框/表格单元里换行更早、行数
更多、撑出框外 → 整页"文字被遮挡、溢出背景框"。

**正确写法**——脚本顶部定义一个字号换算函数，所有 `_set_font` 内部走它：

```python
PX2PT = 72.0 / 96.0  # 0.75
def FS(px):           # css-px font size -> PPTX Pt
    return Pt(px * PX2PT)

def _set_font(run, size, bold=False, color=INK, italic=False):
    run.font.size = FS(size)   # 不是 Pt(size)
    ...
```

> 位置辅助 `P(v)=Inches(v/96.0)` 保持不变（px→inch 本就对）。只需把字号
> 这一路从 `Pt(size)` 换成 `FS(size)`。行间距 `p.space_after` / 文本框
> `margin` 若是按 px 心算的值也要 ×0.75；纯 pt 视觉量（边框 0.5pt）不动。

**验证手法**：解压 PPTX 读 `ppt/slides/slideN.xml`，看 `<a:rPr sz="...">`。
`sz` = pt×100。例如 HTML `font-size:16px` 正确应 `sz="1200"`（12pt），
若看到 `sz="1600"`（16pt）就是漏了缩放、字号偏大 33%。

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
- **字号 px 直接当 Pt → 整页放大 33% 溢出**：`_set_font(r, 16)` 写成
  `Pt(16)` 让字号变 16pt（应是 12pt），所有文字偏大 1.333×，在按 HTML 几何
  尺寸的文本框/表格里换行更早、撑出框外。**必须走 `FS(px)=Pt(px*0.75)`**
  （见上"单位换算铁律"）。验证：XML 里 `sz="1600"` 就是漏了缩放，应是
  `sz="1200"`。位置辅助 `P()` 不变（px→inch 用 96 本就对），只字号这一路
  要换。
- **封面背景图 contain 模式留白边**：`pic_fit`（contain，缩放保留比例居中）
  对 1280×588 框 + 1.78 宽高比的图，按高度缩放得 1046×588，**两侧各留
  117px 白边**。HTML 用的是 `object-fit:cover`（填满+裁剪）。**新增
  `pic_cover()`**：按宽填满（`nw=w, nh=w/img_ratio`），溢出部分用白色矩形
  遮罩（对应 HTML 的 `overflow:hidden`）。判别：图宽高比 < 框宽高比 → 按
  宽缩放裁高度；反之按高缩放裁宽度。cover-bg.jpg 这类全幅封面照一律 cover，
  不要 contain。
- **面包屑（右上角章节导航）CJK 字换行溢出**：宽度估算 `len(s)*7` 对 CJK
  太窄（8.25pt CJK 字约 9px 宽，不是 7px），"分布式"3 字 + 内边距在 35px
  框里被 `word_wrap=True` 拆成"分布\n式"两行，溢出 18px 高的单元格。修复：
  ①宽度按字符类型算（CJK 9px / 拉丁 5px）+ 加大 pad；②文本框传 `wrap=False`
  禁止换行。验证：XML 看 `wrap="none"` 且最右边界 ≤ 1266px（1280-14 右边距）。
- **红色竖排标签超长溢出 + 末字未对齐**：标签 `writing-mode:vertical-rl`
  在 HTML 是连续竖列；PPTX 用 `"\n".join(list(tag))` 逐字一行模拟。固定字号
  16px→12pt 时，"KV Cache 要点"11 字 × 12pt × 1.2 行距 = 158pt = 211px，
  **远超 panel_h=118px**，纵向严重溢出；末字未对齐是 `word_wrap=True` 下窄
  字符异常换行 + 逐 run 居中字宽不一所致。修复（两层）：
  ①**字号自动按高度缩放**：`font_pt = panel_h_px/(1.6*n_lines)`（1.6 = 1.2
  行距 × 96/72），上限 16px、下限 7px。4 字标签得 12pt，11 字标签得 6.7pt
  （恰好不溢出）。
  ②单 run + `"\n".join()`（不逐 run 居中），`word_wrap=False`。
  验证：XML 看 `sz`，11 字标签应 `sz="670"`（6.7pt），4 字标签 `sz="1200"`。
