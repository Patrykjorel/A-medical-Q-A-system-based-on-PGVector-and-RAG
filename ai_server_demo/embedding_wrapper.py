# embedding_wrapper.py
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from config import config

"""
使用 LlamaIndex 官方的 HuggingFaceEmbedding。
"""

# 将 LlamaIndex 的全局嵌入模型实例化
embed_model = HuggingFaceEmbedding(
    model_name=config.EMBEDDING_MODEL_PATH,   # 使用配置中的 embedding 模型路径（bge-base-zh-v1.5）
    device="cpu",  # 如果有显卡可以改为 "cuda"   # 推理设备：CPU（有 GPU 可换 cuda）
    embed_batch_size=10                       # 批量向量化大小
)