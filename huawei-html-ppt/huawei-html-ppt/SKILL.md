---
name: huawei-html-ppt
description: 生成华为官方模板风格的技术汇报 PPT（HTML 格式，16:9，可打印导出 PDF，可转换原生可编辑 PPTX）。当用户要求制作华为风格 PPT、技术汇报 HTML 幻灯片、技术研发体系项目汇报页面时使用；当任务是 PDCP/TDR 等项目评审汇报（给 xlsx 数据 + 往期参考材料）时走 PDCP 分支；当任务是团队"四张地图"（业务地图/组织地图/人才地图/氛围地图，如 LLM组/训练组四张地图、PL 汇报）时走四张地图分支；当用户明确要求可编辑 PPTX 时按 HTML→原生 PPTX 转换流程处理（不分分支）。
---

# 华为风格 HTML PPT 生成

用 HTML/CSS 生成与华为官方 PPT 模板一致的技术汇报幻灯片。

## 任务分流（先判断，再选分支）

- **A. 常规技术汇报页**（给主题/单页内容做华为风格幻灯片）→ 走下面主流程。
- **B. 项目评审汇报（PDCP/TDR 等）**：输入是 xlsx 数据表 + 往期参考 PPT，
  要求"对照参考材料"逐页制作——
  **必读 [references/pdcp-workflow.md](references/pdcp-workflow.md)**
  （样式实抄/页面结构/表格规范）。本分支仍以本 skill 的 CSS 和页面骨架
  为基础，只是叠加 PDCP 专属规范。
- **C. 团队"四张地图"**（业务地图/组织地图/人才地图/氛围地图，技术研发体系
  团队 PL 汇报，如"LLM组四张地图"）——
  **必读 [references/four-maps-workflow.md](references/four-maps-workflow.md)**。
  数据驱动：团队信息 → spec.yaml → HTML 验收 → （用户要求时）模板克隆转
  原生 PPTX。工具在 `tools/four-maps/`（含官方模板与原版图像素材）。
- **交付物默认都是 HTML**；只有用户**明确要求** PPT/PPTX 时才转原生可编辑
  PPTX——A/B 分支走
  **必读 [references/pptx-conversion.md](references/pptx-conversion.md)**；
  C 分支走模板克隆路线（见 four-maps-workflow.md C 节）。
  禁止整页截图贴图。
- 各分支通用的铁律：单文件交付、逐页截图验证、迭代沉淀回 CSS/规范。
- **画图需求**（deck 里的架构图/流程图/拓扑图，或单独要一张图）：
  **必读 [references/drawio-diagram.md](references/drawio-diagram.md)**——用内置
  draw.io server（`tools/drawio-server/`，离线）在浏览器实时预览迭代，交付
  `.drawio` 源文件；嵌入 deck 按"XML 坐标 → 等价内联 SVG"路径（headless 导不出
  PNG，坑见该文档）。

## 工作流程（分支 A：常规汇报）

1. **必读** [references/style-guide.md](references/style-guide.md) —— 颜色、字体、版式、写作风格的完整规范。
2. 生成单个自包含 HTML 文件（`<output名>.html`）：**交付默认把 CSS 内联进
   `<style>`、图片（logo/封面照/结构图）以 base64 内嵌**，只拷一个 HTML 到
   任何机器都不会丢资源（实际教训：deck + 外部 `ppt_assets/` 分发时文件夹
   没跟过去，整页退化为裸 HTML）。开发迭代期间可临时 `<link>` 引用本 skill
   的 `assets/huawei.css`，交付前必须单文件化。
3. 每个 slide 是一个 `<section class="slide ...">`，固定 1280×720，不要让内容溢出。
4. 用浏览器打开验证（截图检查溢出/换行），迭代修正后再交付。推荐配方：
   ```
   chrome.exe --headless --disable-gpu --screenshot=_all.png \
     --window-size=1312,<页数*736+几百> --hide-scrollbars "file:///<URL编码路径>"
   ```
   相邻 `.slide` 的 margin 折叠，截图中**页距 = 736px**（720 + 16），
   第 i 页（0 基）顶部 = `16 + i*736`，用 PIL 按 720 高逐页裁开检查。
   注意：窗口宽用 1280（=画布宽）时页面正好满幅；用更宽窗口会把 html/body
   的 #555 背景截进两侧（转 PPT 后成为黑边）。

## 结构模板

参考 [assets/example.html](assets/example.html) —— 包含全部页面类型的可运行示例
（流程图/架构图类内容另见 [references/drawio-diagram.md](references/drawio-diagram.md)
的 draw.io 画图流程）：

- **封面** `slide--cover`：`cover-photo`（背景图）+ `cover-rect`（红 L 角标）+
  `cover-title` + `cover-meta`（部门/作者/日期三行）+ `security` + `cover-logo`。
- **目录** `slide--toc`：`toc-heading`"目录" + `toc-underline` 红短线 +
  `toc-list`（当前章 `li.active` 红色加大）。章节过渡时重复目录页并切换高亮。
- **摘要** `slide--content`：结论式红标题 + **一个**通栏"分析结论"
  `label-block`（红标签，➢ 要点，黑字+红数字，高 ≤1/4 页）+ 双卡片：架构概览
  SVG 图 + 参数对比表（3 列 `维度|本模型|对方`，拉伸行高填满卡片）。标签一律
  红色、不用 KPI 数字卡/独立指标条/备注列（详见 style-guide"摘要页"）。
- **内容页** `slide--content`：`content-header > content-title`（红色加粗，可带
  【前缀】）+ `content-body`。右上角 `crumbs` 章节导航（当前项 `current`；
  ≥5 项加 `dense`）。页脚 `footer`（Page X/Y + Huawei Confidential + logo）必加。
- **结束页**：白底 "Thank you." + 愿景文案 + 版权 + logo。

## 组件速查（CSS 已定义，直接用 class）

| 组件 | class | 用途 |
|---|---|---|
| 标签块 | `.label-blocks > .label-block > .tag + .panel` | 页首 目标/挑战/进展/结论/约束 竖排标签 + 灰底要点；**标签一律红色**（.blue 变体已并入红色，勿用灰标签） |
| 卡片 | `.card` / `.card.accent` + `.card-tab`（骑线标题）/ `.card-title` | 围栏式模块；**内嵌 SVG/大图时 card 与内容层加 `min-height:0`**（否则固有高度撑破被 overflow 裁底边） |
| 表格 | `table.hw`（表头 `#F2F2F2` 灰底近黑粗体——模板实抄规格；`td.hl` 红色关键值，`td.left` 左对齐；内容字色：前缀/责任人/决策建议 `#0000FF`、【技术点名】红粗） | 数据表 |
| 流程图 | `.flow > .node (.blue/.yellow/.pink/.gray) + .arrow` | 直角节点+箭头 |
| KPI | `.kpis > .kpi > .num + .lbl` | 指标块 |
| 多栏 | `.cols > *` | 等宽分栏 |
| 强调 | `.red .blue .green .orange .small .tiny` | 红色强调/状态色 |
| 紧凑/宽松表 | `table.hw.compact` / `table.hw.roomy` | 高密度页 / 单表页撑满 |

## 硬性规则

- 页标题 = 结论，含量化数字（"吞吐提升10%+"），不用"XX介绍"。
- **结论先行**（通用原则，适用于一切组件，不限于标签块）：判断/导读类元素
  （标签块、KPI 摘要条、口径/图例说明）放标题正下方；证据/明细（表格、图、
  推导）居中；页尾只放来源/口径脚注，不放判断性内容。
  **标签块一律在内容上方、间距 ≥20px**（用户反馈：别跟内容黏在一起、
  别放底下——"使用约束"类块同样上置，详见 style-guide"版面通用原则"）。
  **标签块的竖排标签一律红色**（用户反馈：灰标签怪）；.blue 变体仅是兼容
  别名、色值已并入红，新页面不要再写 `.blue`。
- **色卡纪律**：除图片资产外，一切元素只用模板图表色卡 6 色（亮红 `#E9002F`、
  深红 `#C00000`、琥珀 `#FBA000`、灰 `#C5C5C5`/`#929292`/`#666666`）+
  黑白灰中性（`#1D1D1A` 正文、`#EBEBEB`/`#F2F2F2` 底、tint `#FCE0E6`/`#FDEED2`）。
  不引入任何卡外颜色（蓝/绿/青等一律不用，详见 style-guide 第 1 节）。
- 状态语义（色卡内表达）：正向/关键=红 `#C00000`，警示/注意=琥珀 `#FBA000`
  （仅色块，小字警示用红），基线/对方/挑战=深灰 `#666666`。
- 正文 16px 起步可到 14px，脚注 12px；一页一个主题，允许高密度但必须分区。
- **页面必须撑满，不留大片底部空白**：单表页用 `table.hw.roomy`，
  内容少时加大字号，让 `.content-body` 的 space-evenly 均匀分布生效。
- **反 AI 味**：摘要页禁 KPI 数字卡和非红标签块；不用渐变/圆角彩卡/emoji/
  纯装饰竖条；装饰必须有信息含义（详见 style-guide 第 5 节）。
- 页脚 `Page X/Y` 全场唯一，拆页/插页后重排序号。
- 资源路径：交付 deck 一律单文件自包含（CSS 内联 + 图片 base64）；开发期
  临时引用时用相对路径指向本 skill 的 assets，或复制
  `huawei-logo.png` / `cover-bg.jpg` 到输出目录同侧。
  **改了 skill 的 CSS 后，凡是仍以 `<link>` 引用旧副本的 deck 必须同步重打包**
  （内联交付的 deck 不受 skill 后续改动影响，也不会被丢资源问题坑）。
- 导出 PDF：Chrome 打开 → 打印 → 目标"另存为 PDF"（CSS 已含 @page 1280×720）。

## 迭代约定

用户会用实际例子试跑并反馈。修正时优先改 CSS 令牌/组件（assets/huawei.css）
而不是在生成页里写一次性样式，让规范沉淀回设计系统。
