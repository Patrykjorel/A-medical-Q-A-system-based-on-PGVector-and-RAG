# 系统对比表（修订版）

面向论文或产品介绍时使用。相较初版：**弱化绝对化表述**、**与竞品对齐可比维度**、**与本仓库实现一致**（含可选联网检索、Reranker 算力说明等）。

---

## English（便于直接放入英文稿）

| Feature | ChatGPT | DeepSeek | HuatuoGPT | This System |
|--------|---------|----------|-----------|-------------|
| **Deployment mode** | Cloud commercial service | Cloud commercial service | Open-source, locally deployable | On-premise layered stack (app / LLM & RAG / PostgreSQL+PGVector); **optional** Internet search via third-party API |
| **Data privacy** | User content processed on provider infrastructure | User content processed on provider infrastructure | Supports local deployment for private use | Business vectors and documents stored locally; **if web search is enabled, queries are sent to the search provider** |
| **Private medical knowledge** | Cloud-side knowledge features (e.g., file-backed GPTs); **not** a user-hosted on-prem KB product | No first-party integrated **local** document product; private corpus typically via **user-built** RAG on API | Primarily **pretrained** medical knowledge; check specific release for retrieval plugins | Local ingestion of medical documents: PDF (incl. scanned), TXT, MD; corpus stays under user control |
| **Knowledge enhancement** | General-purpose LLM generation | General-purpose LLM generation | Medical-domain pretrained language model | RAG over PGVector; **file-level** metadata filtering (e.g., selected documents); optional BGE reranking and score-based filtering |
| **Hardware requirement** | No local deployment | No local deployment | **GPU often recommended** for acceptable latency; CPU feasible for smaller or quantized setups in practice | **CPU-capable** end-to-end; **GPU recommended** for BGE reranker latency and larger local LLMs |
| **Semantic cache** | Public product does not expose an **embedding similarity** cache like a vector DB table | Same | Not a highlighted feature in typical releases | **Embedding-based** Q&A semantic cache implemented with **PGVector** |
| **Multi-turn conversation** | Supported | Supported | Supported | Session management with contextual dialogue (e.g., bounded history window) |
| **Medical-oriented mechanisms** | General dialogue | General dialogue | Medical dialogue-oriented modeling | Medical prompt framing, OCR-oriented document parsing, BGE reranking, similarity/rerank thresholds |

### Notes（英文脚注）

1. **Fair comparison**: Consumer web UIs are compared to self-hosted stacks where dimensions differ; enterprise offerings (ChatGPT Enterprise, etc.) may add DLP, VPC, or regional hosting—not full on-premise vector ownership by default.
2. **“Semantic cache”**: Distinct from API **prompt caching** (prefix reuse for cost/latency); this table’s “semantic cache” means **near-duplicate question matching via embeddings** stored in PGVector.

---

## 中文对照（便于中文论文或答辩幻灯）

| 维度 | ChatGPT | DeepSeek | 华佗 GPT（HuatuoGPT） | 本系统 |
|------|---------|----------|----------------------|--------|
| **部署形态** | 云端商业化服务 | 云端商业化服务 | 开源、可本地部署 | 本地化分层架构（应用 / LLM 与 RAG / 数据库与向量扩展）；**可选** 第三方联网检索 API |
| **数据隐私** | 数据在服务商基础设施处理 | 数据在服务商基础设施处理 | 支持本地私有化部署 | 业务向量与文档默认落本地；**开启联网检索时，检索请求会发往检索服务方** |
| **私有医学知识** | 云端侧知识能力（如基于文件的 GPT），**非**用户机房内托管的一体化本地知识库产品 | **无官方一体化本地文档库产品**；私有语料多依赖用户基于 API **自建 RAG** | 以**预训练医学知识**为主；具体版本是否带检索需对照发行说明 | 支持 PDF（含扫描件）、TXT、MD 等入库；语料与用户可控、本地存储 |
| **知识增强方式** | 通用大模型生成 | 通用大模型生成 | 医学领域预训练语言模型 | 基于 PGVector 的 RAG；**按文档/文件维度**的元数据过滤；可选 BGE 重排与分数过滤 |
| **硬件要求** | 不要求本地环境 | 不要求本地环境 | **常用 GPU** 以保证可接受延迟；CPU 多用于小规模或量化场景 | **全流程可在 CPU 上运行**；BGE 重排与较大本地模型 **建议 GPU** 以降低延迟 |
| **语义缓存** | 面向大众产品未公开「向量语义相似命中」类缓存能力 | 同上 | 发行版通常不强调该能力 | 基于 **PGVector** 的嵌入语义问答缓存 |
| **多轮对话** | 支持 | 支持 | 支持 | 会话管理与上下文对话（如限制窗口的历史拼接） |
| **医学相关机制** | 通用对话 | 通用对话 | 面向医学对话的建模 | 医学向提示词、面向 OCR 的文档解析管线、BGE 重排与相似度阈值等 |

### 脚注（中文）

1. **可比性**：网页消费级产品与自建系统在维度上不完全对等；企业版（如专线、区域托管、DLP）可改善合规性，但未必等同于向量与文档完全自持。
2. **「语义缓存」**：与 API **提示缓存**（前缀复用降本降延迟）不同；此处特指将历史问答嵌入存入向量库、按相似度命中复用的机制。

---

*修订说明：与仓库实现一致处包括——`semantic_cache` / PGVector、`rag_core` 中 BGE rerank 与 `file_name` 过滤、`web_search` 可选公网检索。*
