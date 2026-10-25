# 缺少材料时的证据获取

先用用户提供的报告/源码/配置/基准。用户已确认准确时沿用，除非本次明确要求审计。

| 来源 | 主要用途 | 不能替代 |
|---|---|---|
| https://github.com/maoxx241/se-tools | 分析工具、计算方法、参数与部署推演入口 | 官方模型配置、硬件实测 |
| https://gitcode.com/gcw_hasgjVbP/model_analysis | 模型分析流程、配置与计算产物的组织 | 被分析版本的实际 forward |
| 模型发布方 Hugging Face 仓库 | config、层型、维度、权重索引、建模代码 | Ascend 上的运行支持与实测 |
| https://github.com/vllm-project/vllm-ascend | Attention 后端、Cache、通信与并行实现、兼容约束 | 上游模型算法说明或实际收益 |
| https://github.com/vllm-project/vllm | 按实际调用链检查上游调度、批处理、KV/Prefix Cache 管理、模型执行及并行分组 | Ascend patch 后的实际行为、NPU 算子支持或硬件实测 |

记录仓库 revision、路径、符号/章节、访问日期和证据等级，来源元数据放备注。模型身份不明时不猜 HF 仓库名；先找发布方链接或让用户补充身份信息。

画图前将 config 和 forward 的顺序交叉核对，再检查运行后端如何实现。不把源码某分支存在等同于任意型号、任意版本可用。以 Kimi K3.1 为例，先保留已验证 K3 主干，再定位 K3.1 新增/修改的子图，并把增量放大；不能拿其他模型的数值或层数填空。

涉及调度与缓存生命周期时，先检查 vLLM-Ascend 的版本依赖、插件注册、patch 和覆盖，再沿调用链阅读对应版本的上游 vLLM。没有覆盖且调用解析到上游时，才按上游实现说明行为。不要把两个仓库各自的最新 main 直接拼在一起推导支持性；详细步骤见 [runtime-static-analysis.md](runtime-static-analysis.md)。

下载公开文件可用网络；本地保密材料不发送到搜索、云文档、外部绘图、翻译或生成服务。页面说明不要夹带本机私有路径或未授权发布的数据。
