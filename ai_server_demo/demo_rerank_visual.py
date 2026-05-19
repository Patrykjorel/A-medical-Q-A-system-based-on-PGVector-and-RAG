import numpy as np
from FlagEmbedding import FlagReranker
from embedding_wrapper import embed_model
from config import config

# =====================================================================
# 初始化重排模型 (Cross-Encoder 交叉编码器)
# FlagReranker: 专门用于对文本对进行打分重排的模型类
# config.RERANKER_MODEL_NAME: 指向本地权重目录 models/bge-reranker-v2-m3
# use_fp16: 是否使用半精度推理（开启可加速并降低显存/内存占用）
# =====================================================================
reranker = FlagReranker(config.RERANKER_MODEL_NAME, use_fp16=config.RERANK_USE_FP16)

# query: 模拟用户提出的真实痛点问题
query = "如何治疗感冒？"

# passages: 模拟【第一阶段：粗筛召回 (Recall)】拿回来的候选文本块 (Chunks)。
# 现象：这些段落都包含"感冒"或相关医学术语，字面上非常相似。
# 问题：但从逻辑上看，并非每一条都能直接回答“如何治疗”。
passages = [
    "感冒通常需要多休息、多喝水，症状严重时可服用退烧药。",  # 完美回答
    "流感疫苗可以预防流感，建议每年接种。",  # 答非所问（预防）
    "感冒是自限性疾病，一般7-10天自愈。",  # 补充信息
    "抗生素对病毒性感冒无效，不要滥用。",  # 避坑指南
    "中医认为感冒分为风寒和风热两种类型。"  # 偏向分类，未答治疗
]

print("=" * 60)
print("【第一阶段】向量检索阶段（双编码器 Bi-Encoder 机制）")
print("说明: 分别计算问题向量和段落向量，比较它们在三维/多维空间中的“距离”")
print("=" * 60)

# get_text_embedding: 调用 Embedding 模型，将输入文本降维映射为稠密向量 (Dense Vector)
# query_emb: 代表“问题”的向量表示
query_emb = embed_model.get_text_embedding(query)

for i, p in enumerate(passages):
    # p_emb: 代表“候选段落”的向量表示
    p_emb = embed_model.get_text_embedding(p)

    # 核心算法: 计算余弦相似度 (Cosine Similarity)
    # 公式: 向量点积 / (两个向量的模长乘积)
    # 含义: sim 值越接近1，说明两段文本在字面或浅层语义上越“相近”，但这不代表逻辑对齐。
    sim = np.dot(query_emb, p_emb) / (np.linalg.norm(query_emb) * np.linalg.norm(p_emb))
    print(f"[{i + 1}] 粗筛相似度: {sim:.4f} | 内容: {p[:30]}...")

print("\n" + "=" * 60)
print("【第二阶段】BGE Reranker 打分阶段（交叉编码器 Cross-Encoder 机制）")
print("说明: 把问题和段落合并输入模型，运用 Attention 机制看词与词之间的深度逻辑关系")
print("=" * 60)

# pairs: 构建 Rerank 模型所要求的输入格式
# 格式要求为“文本对”的列表：[[问题, 段落1], [问题, 段落2], ...]
pairs = [[query, p] for p in passages]

# compute_score: Rerank 核心打分函数
# 机制: 模型不再计算几何距离，而是深层推理“段落 p 是否能完美解答问题 query”。
# scores: 返回一个浮点数列表，数值越大，逻辑相关度越高（可为负数）
scores = reranker.compute_score(pairs)

# ranked: 数据组合与重排序
# zip 负责把 passages 和 scores 缝合在一起
# sorted 结合 lambda 表达式，根据分数 x[1] 进行从大到小的降序排列 (reverse=True)
ranked = sorted(zip(passages, scores), key=lambda x: x[1], reverse=True)

for i, (doc, score) in enumerate(ranked):
    # 此处输出重排过的高质量排序结果
    print(f"[{i + 1}] 精排分数: {score:.4f} | 内容: {doc[:30]}...")
