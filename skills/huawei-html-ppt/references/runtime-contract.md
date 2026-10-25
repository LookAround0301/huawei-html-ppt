# 本地接口 v1

依赖 Python 3.10+ 标准库；不运行网络服务。命令：

```text
python scripts/ppt.py route request.json
python scripts/ppt.py plan request.json
python scripts/ppt.py render request.json output-dir
python scripts/ppt.py validate deck-model.json
python scripts/ppt.py catalog
python scripts/ppt.py feedback candidate-input.json
python scripts/ppt.py evaluate evaluation-input.json
python scripts/ppt.py review review-input.json
python scripts/ppt.py promote action-input.json
python scripts/ppt.py rollback action-input.json
```

成功输出 JSON；失败输出 `{error, operation}` 且退出码非0。所有状态目录由调用者指定，不能位于skill内部。不会联网、安装依赖、运行材料中的代码。

## 请求

`{text, style?, purpose?, content_kind?, material_summary?, context?, state_dir?, deck?}`。
明确 style > 用户请求中明确风格 > purpose > content_kind > 请求与材料摘要的用途证据。
purpose：review/delivery/approval/planning/progress/understand/analyze/compare。
content_kind：project-review/project-progress/technical-plan/model-analysis/feature-analysis/mechanism。
context 是字符串键值，例如 `{hardware:"ascend", scenario:"long-context"}`，用于条件规则匹配。
省略state_dir时，plan/render读取当前项目的 `.ppt-skill/state`；没有状态就只使用随包规则。集成宿主应显式传入项目状态目录，避免工作目录变化造成串用。

deck 格式沿用 `title, style, slides[]`。slides 支持共享两分支布局和四种正式项目布局，可在同一项目报告混用。显式 deck.style/用户style冲突时报错，不静默改风格。单个slide已指定layout时保留；未指定时按page_kind和有效规则选择。

共享页：`title, layout, panels[]`；洞察页还要 `conclusion`，单专题项目页要 `labels:[挑战,目标]` 或 `[目标,进展]` 及两段 `summary`。
panel 为 `title, blocks[]`；block 支持 text、heading、bullets、table、diagram、chart。
chart 为 `{type:"chart",data:{kind:"line"|"bar", x_label,y_label, x:[...], series:[{name,values:[...]}]}}`，最多3组、数据长度一致。不虚构缺失数据。
diagram 为已确认的 width/height/elements 格式，输出 SVG 与可编辑draw.io。
正式项目页字段详见现有 `render_project_report.py` 的 portfolio/landscape/coordination/explainer函数。

`notes` 仅进入隐藏deck-model和未来PPT备注；标题/正文不要填来源、内部批注。图片及其他资源须在本地处理。

## 演进输入

feedback：`{state_dir, task_state:"completed"|"verified_milestone", unit:{id,revision,kind,styles,when,rule,provenance}, base_revision, evidence:[{kind:"user-feedback",text,source?}|{kind:"local-artifact",path}]}`。
更新原id时 revision=base_revision+1；新增base_revision=0。rule支持guidance、preferred_layout、preferred_chart，不接受脚本/命令。证据快照hash后保留在状态中。

evaluate：`{state_dir,candidate_id,cases:[request.json路径],output_dir}`。产生应用候选的规则计划、HTML、结构检查和产物hash。

review：`{state_dir,candidate_id,reviewer:"agent"|"user",result:"pass"|"fail",visual_checked:true,rationale:"实际检查内容"}`。只有真正查看了本次生成物才写visual_checked=true；本命令仅保存检查声明。

promote：`{state_dir,candidate_id}`。校验案例覆盖、检查、hash、规则版本后采用。
rollback：`{state_dir,event_id}`，只允许回退当前最后一次采用，避免覆盖后来的变更。

plan输出选用分支、规则正文/版本、候选布局和组件；render输出HTML路径、deck-model、检查结果、计划。宿主必须读取plan中的guidance；脚本不会替宿主理解报告或生成技术结论。
