# 二维模型结构图组件

`scripts/model_architecture.cjs` 提供 `Scene`、`moduleGraph`、`backbone`、`svg`、`drawio` 和 `audit`。适用于已核对结构的二维模型图；具体页画什么由内容决定，不要求工作台、固定版式或局部放大。

- 输入输出只用英文文字标签；缓存为矩形，专家组可用简洁堆叠矩形。
- 实际计算、控制和状态读写关系先核对，再组织节点。使用具名端口；`Scene.path` 生成水平/垂直折线，SVG 与 draw.io 使用同一条路线。
- 运行实现图按 [源码与 shape 规则](runtime-static-analysis.md#把实现画进模型结构) 表达关键融合与条件路径。shape 用普通英文/符号文字，优先标实际发生变化的边和节点，不恢复装饰矩阵图标。
- `audit` 检查节点边界、连线是否正交及图内中文。仍需渲染检查穿字、穿框、拐点、图例、字号和路径含义。
- 保存结构参数、场景 JSON、组件版本/哈希、SVG、原生 draw.io 与审阅结果；报告可嵌入本地 PNG。图片来源记录 `kind: generated` 及上述文件，不把新绘图冒称仓库原图。
- 此引擎是现有 Python 组件之外的可选生成方式，需要本机 Node。生成图像时单独运行，不改变纯 Python 的文稿接口。
- 显式模型 JSON 的层数、维度和格式由本次材料提供，未知模块用 `Scene` 扩展；不据模型名猜参数或承诺部署支持。

当前内置示意包括 KDA、门控 MLA/DSA、LatentMoE、Dense、GQA 与 AttnRes 残差。它们不是所有同类模型的通用实现；门控、低秩投影、共享分支和状态布局必须按本次源码删改，不适用时直接用 `Scene` 组装。具体算法仍按当前源码/人工基准核对。嵌入生成图时使用其独立语义和连线审阅记录；旧 `diagram` 数据继续沿用组件重放契约。

## 接口与使用范围

- `Scene(width, height, title)`：建立画布；`node(id,x,y,w,h,label,options)`、`frame(...)`、`text(...)` 组织二维结构，坐标均为逻辑像素。
- `edge(source,target,{sourcePort,targetPort,via,role})`：端口用 `n/s/e/w` 或 `[0..1,0..1]`。显式 `via` 用来避开其他节点；正交路由不等于自动避障。
- 用 `node` 的 `shape: 'label'` 标输入输出，`shape: 'memory'` 标矩形缓存。shape 注释可用节点 `sub` 或 `text`，与图源一起保留。
- `moduleGraph(scene,module,prefix,slot)` / `backbone(...)` 提供参数化的模型语义骨架。融合边界、P/D、量化和通信随实现变化时，用 `Scene` 按本次调用链组装，不能把内置骨架冒充真实执行图。
- `svg(scene)`、`drawio(scene)` 导出同一场景；`audit(scene)` 返回结构检查与 `visual_review_required`，不代表已经视觉验收。PNG 在本地用 SVG 渲染后得到，包内不携带浏览器、Node 或模型配置。

图形组件不内置具体模型的层数、显存或硬件配方，不下载数据，也不自动推断某模型已支持的融合内核。使用者负责按源码核对本次节点、shape 和启用条件。
