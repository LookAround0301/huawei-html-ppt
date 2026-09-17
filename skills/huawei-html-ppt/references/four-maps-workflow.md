# 四张地图分支（团队 PL 汇报：业务/组织/人才/氛围）

适用于：用户要求为某个团队/小组制作"四张地图"（部门A体系的团队
汇报材料，如"LLM组四张地图""训练组四张地图"），或要求"参照样板组模板
生成其他组的四张地图"。输入通常是团队信息（口头描述/笔记/旧版 PPTX）。
普通技术汇报走主流程，PDCP 评审走 PDCP 分支，不进本分支。

核心纪律：
1. **版式照样板组官方模板抄，不要自创**——封面橙带、页眉导航、页脚、
   表格样式、胜任度图例都已用原版素材/实测参数复刻，禁止改设计。
2. **spec.yaml 是唯一数据源**——HTML（验收）与 PPTX（交付）共用同一份 spec，
   改内容只改 spec 重渲染，禁止两边各改各的。
3. **防泄漏兜底**——spec 未提供的版块渲染为"（待补充）"或删表，
   绝不残留样板组的人员信息；交付前抽查一遍。

工具位置：`tools/four-maps/`（本 skill 内）
- `render_html.py` — HTML 渲染器（验收用，素材相对自身路径 `assets/` 解析）
- `generate.py` — 原生 PPTX 生成器（模板克隆 + PowerPoint COM 重排）
- `export_png.py` — PPTX 逐页 PNG 导出（PowerPoint COM）
- `assets/template.pptx` — 样板组官方模板（7 页）
- `assets/bg_cover.png / footer_strip.png / cover_logo.png` — 从原 PPT 提取的
  封面背景/页脚条/Logo，HTML 渲染时 base64 内嵌
- `spec_example.yaml` — 完整示例（样板组真实数据，HTML/PPTX 双路线已回环验证）

依赖：python-pptx、pyyaml、pywin32（COM：本机需装 PowerPoint；不可用时
HTML 不受影响，PPTX 仅跳过重排并告警）。

---

## A. 信息收集（缺什么问什么）

**meta**：组名（如"XX部门ALLM组"）、PL 姓名、工号

| 版块 | 内容 |
|---|---|
| 业务地图 | 3 个左右战略项：红色标题 + 若干子项 + 关键挑战（可选） |
| 组织地图 | 特性组列表：标题 + 成员（分工/角色 SE·DV/姓名/人岗/任职/年限/胜任度/落地仓库）+ 合作团队 |
| 人才地图 | 岗位表（岗位类型/核心职责/职级分布/经验要求/当前人数/缺口）+ 招聘表（岗位/方向/人力需求/引入策略） |
| 氛围地图 | 团队导向氛围（陈述句 + 行动措施，可含关键 GAP 点）+ 活动氛围 |
| 组织结构图 | 缺省从组织地图自动派生，一般不用单独提供 |

用户给旧版 PPTX 时：用 zipfile/python-pptx 解析抽取文字，写入 UTF-8 dump
再 Read（控制台 GBK 乱码，同 PDCP 分支 A1 纪律）。

## B. spec.yaml 格式（完整语法）

完整可运行示例见 `tools/four-maps/spec_example.yaml`。要点：

```yaml
meta: {group_name: XX部门AXX组, pl_name: 张三, pl_id: "0086xxxx"}
business_map:
  items:
    - header: 1.红色战略标题…
      subs:
        - text: 普通子项
        - {lead: 关键挑战：, text: "..."}     # lead=加粗前缀; 文本内 \n=换行
org_map:
  features:
    - title: 特性组名
      col: 0                                  # 可选: 固定列(0左/1右), 复刻手工布局
      w: 4.7                                  # 可选: 表宽(inch), 如 FA 表给图例让位
      landing: true                           # 可选: 加"落地"列(5列)
      members:
        - {feature: 分工, role: SE, name: 张三, grade: "16 / 3 / 5",
           competency: 高, landing: 仓库B}
      partners: 合作团队列表                   # 自动加"合作团队："前缀
    - title: 大特性组
      sections:                               # 可选: 多小节(各自副标题/成员/合作团队)
        - {subtitle: 子方向A, members: [...], partners: ...}
talent_map:
  positions: [["PL", "1、xxx\n2、xxx", "17级", "经验要求", "1", "NA"]]
  hiring:    [["SE（16+级）", "方向", "2人", "校招+内引"],
              ["", "方向2", "1人", "内引"]]   # 第一列空串=延续上行(rowspan合并)
atmosphere_map:
  sections:
    - title: 团队导向氛围：
      statement: 打造一个…的团队。
      blocks:
        - header: 行动措施
          items:
            - {lead: 关键GAP点：, text: ...}
            - text: 普通条目
org_map_v2:
  group: XX技术开发组        # 第7页顶部盒子组名; 缺省=组名去掉"XX部门A"类前缀(截到"技术开发"为止)
  features: null             # null=自动从 org_map 派生(去落地列紧凑版); 也可完全覆盖
```

**胜任度 competency 取值**（打在姓名单元格）：
`高`/胜任度高=绿 92D050，`胜任`=黄 FFFF00，`基本`/基本胜任=橙 FFC000，
`不胜任`/暂不胜任=红 FF0000，不填=无色（SE 整体负责人常不评）。
特殊强调：talent 表单元格值加 `[red]` 前缀=红色加粗（如缺口 `"[red]2/4"`）。
自动样式：业务地图子项 "前缀：内容" 且前缀≤14字符时前缀自动加粗+悬挂对齐；
灰框内容 flex 均布撑满，无需手工调间距。

## C. 生成与验收流程

1. **写 spec.yaml**（放工作目录，如 `llm组_spec.yaml`）。
2. **渲染 HTML 交用户验收**：
   ```bash
   python ${CLAUDE_SKILL_DIR}/tools/four-maps/render_html.py --spec spec.yaml \
     --out "<组名>四张地图.html"          # 绝对路径! 相对路径会写错目录
   ```
   页序固定 7 页：1封面 2业务 3组织 4人才 5氛围 6结束页 7组织结构图。
   `--slide N` 只渲染第 N 页供截图自检（Chrome headless 配方见主流程 SKILL.md）。
   改内容只改 spec 重渲染。
3. **用户明确要 PPTX 时**转原生 PPT（模板克隆路线，不走 pptx-conversion.md 的
   HTML 解析路线）：
   ```bash
   python ${CLAUDE_SKILL_DIR}/tools/four-maps/generate.py --spec spec.yaml \
     --template ${CLAUDE_SKILL_DIR}/tools/four-maps/assets/template.pptx \
     --out "<组名>四张地图.pptx"
   python ${CLAUDE_SKILL_DIR}/tools/four-maps/export_png.py "<组名>四张地图.pptx" <预览目录>
   ```
   逐页 PNG 抽查：组织地图表格无重叠越界（COM 重排超页会打警告→提醒精简）、
   文本无溢出、胜任度颜色、封面组名/工号。
   注意 COM 打开中文路径可能 E_FAIL——先拷成 ASCII 文件名再操作。

## D. 本分支特有规则与坑

- **内容量对齐模板**：业务地图 ~16 段、组织地图 ≤6 张表。组织地图表格总高
  超过页高会溢出/告警——需用户精简成员或合并特性组。
- **组织地图布局**：spec 顺序 + `col` 显式分列可复刻任意手工布局；未指定时
  按估算高度降序贪心均衡两列。大表(成员多)优先放右列（右列宽 681px）。
- **第 7 页组织结构图**：HTML 端完整支持（组名盒子+连接线+橙黄标题紧凑表+
  胜任度说明框）；**PPTX 端 generate.py 尚未实现该页内容替换**——未提供
  org_map_v2.features 时自动删除该页（避免残留样板数据）。若用户要求
  PPTX 必须含第 7 页，如实告知该限制。
- 文本里不要用长串空格做对齐（会溢出），多行内容用 `\n`。
- 模板第 7 页原版含重复的遗留表（稀疏量化×2、EPLB×2），自动派生只生成
  干净的每特性一张。
- 输出文件名 `<组名>四张地图.pptx` / `.html`，放用户工作目录（绝对路径）。
