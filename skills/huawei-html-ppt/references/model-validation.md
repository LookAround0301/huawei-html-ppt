# 模型分析的基准、DFG 与场景校验

当任务涉及人工核对的基准、执行流程图或多设备部署时使用。本规范补充常规参数/单位核验；不把某次模型的硬件配置当作通用默认值。

## 1. 先固定基准和统计范围

- 用户明确指定的基准优先于模板默认参数。保留原文件，记录 SHA-256、工作表/单元格、代码版本与采集时间。
- 区分源 checkpoint、离线重打包结果、运行时驻留格式。部署新增的旋转矩阵、scale 或拷贝单独列项，不能混入源模型参数总量。
- 激活参数明确列出是否计入 embedding、LM head、视觉分支和共享专家。不同口径先转换，再比较差异。
- 基准 HTML 与 Excel 有细项不一致时记录差额和来源，不强制把一方改成另一方。权重索引的 total_size 不是逐 Tensor shape/dtype 的替代证据。

## 2. 从 forward 核验 DFG，不从名称猜执行顺序

- 先读取实际 forward、配置开关和所用后端。构造函数声明了模块，不代表该分支执行，也不证明调用顺序。
- 若已确认某 attention 启用 NoPE，图中不能继续画旋转位置编码。保留实际参与计算的通道；如 Kimi 的 `qk_rope_head_dim` 字段仍为 64，不能据字段名补画 RoPE，也不能删掉这 64 维。
- 检查 norm、gate、投影、dispatch、combine 和残差在实际代码中的先后顺序。Kimi 的 routed RMSNorm 位于专家结果加权合并后、latent up 前；它不是所有 MoE 的通用规则。
- 图和算子表共用带稳定 ID 的结构化节点/边。节点应记录语义操作（如 `rotary_embedding`、`combine`、`routed_rms_norm`），不能只保存显示文字。
- 对已确认的顺序建立路径约束，如 `combine → routed_norm → latent_up`；检查反向路径不存在。渲染后再看连线是否穿过无关节点、gate/共享分支是否丢失。
- 未取得当前版本 forward 时标明参考实现与推断范围。仍须修正已有代码足以确认的错误，不能用“待验证”掩盖已知冲突。

## 3. 比较容量前逐场景对齐

每个场景按需显式记录：阶段、模型范围、节点/卡/die/rank 数、TP/EP/PP、各类独立 TP、CP/DCP、PP 层分配、token/batch/并发、权重配方、主缓存与 Indexer dtype、block、state dtype 和附加 buffer。

- 分别定义 Prefill 和 Decode。已有基准使用 PP/CP/DCP 时，不得因实现方便退回 PP1/CP1/DCP1，或静默缩短上下文。
- 分别定义 A3/A5 或其他目标平台的设备寻址、容量、量化和通信路径；没有证据时保留未知，不从另一平台外推。
- `FP8` 标签不足以确定权重字节。检查是否为 MXFP8、group size 与 scale dtype；源配方、基准公式或张量头支持时才映射。权重精度不自动决定 KV 或通信精度。
- 在 TP 切分后的局部 shape 上计算 packing、scale 和每通道附加量；专家不整除时按真实放置规则处理。
- PP 容量使用 `max_stage(weight + cache + buffer + 已建模运行时项)`。不要把不同 stage 的各项最大值相加，也不要把当前 stage 的值当作整个部署最大值。
- 将基准值、复算值与差额并列。不同条件的容量值先标为“场景不同”，不能直接当成算术错误或性能提升。

## 4. 交付前的证据

1. 核验配置字段、层号基准、全层覆盖与 Tensor 名称/数量；再按实际证据核验 shape、dtype、重复和分片。
2. 比对每个基准场景的完整输入、逐行权重、当前 stage 及最大 stage 汇总。保存差异，而不是只报告总参数一致。
3. 独立复核关键算式；工作簿改参重算、保存后的公式/缓存、原生 Excel 行为分别记录验证状态。
4. 检查 DFG 的开关约束和执行路径；确认 HTML 使用的图数据与核验数据同一版本。
5. 对本次修正增加少量有效回归：人为插入禁用的 RoPE、把 norm 移到错误位置、替换 token/量化/并行参数、把 stage0 当最大值，应当被拒绝。避免只测试标题或固定文案。

## 可选的确定性校验脚本

本 skill 附带 `scripts/validate_model_artifacts.py`（仅 Python 标准库）。适合已有结构化图、场景和结果的任务；无需为了简单问答建立空文件。

```text
python scripts/validate_model_artifacts.py --contract /absolute/path/validation-contract.json --output /absolute/path/checks.json
```

contract 中的 `files` 路径相对 contract 文件，包括：

- `config`：模型配置。
- `graphs`：图字典；每图含 `nodes`（ID → 含 `op` 的节点）和 `edges`（起止 ID）。
- `profiles`：`scenarios` 数组，含 `name`、`inputs`、`partitions`、`recipe`、`phase`、`scope`、`current_stage`、基准当前 stage 四项 GiB 与 `expected_max_total_gib`。
- `results`：`scenarios` 数组，含相同输入与每 stage 的 `weight_bytes`、`cache_bytes`、`buffer_bytes`、`total_bytes`，以及选中的 `max_stage` 和最大 `total_bytes`。
- 可选 `html`：包含 `flow-graph-sha256` 元数据。其值是 graphs 对象按 UTF-8、`ensure_ascii=False`、排序键、紧凑 JSON 序列化后的 SHA-256。

`graph_rules` 可设置依据配置的 `when`、`forbid_ops`、`ordered_nodes`、`node_ops`。这些约束必须来自当前任务的已检查证据，不得从 Kimi 示例泛化到所有模型。脚本检验的是与声明基准的一致性，不证明基准正确或硬件上可以运行。
