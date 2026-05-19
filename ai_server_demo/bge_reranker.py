# bge_reranker.py
from typing import List, Tuple
from dataclasses import dataclass
from FlagEmbedding import FlagReranker
from config import config


@dataclass
class RerankItem:
    text: str
    metadata: dict
    vector_score: float | None
    rerank_score: float


_reranker_singleton: FlagReranker | None = None


def get_bge_reranker() -> FlagReranker:
    global _reranker_singleton
    if _reranker_singleton is None:
        _reranker_singleton = FlagReranker(
            config.RERANKER_MODEL_NAME,
            use_fp16=getattr(config, "RERANK_USE_FP16", False)
        )
    return _reranker_singleton


def rerank_nodes(query: str, candidates: List[Tuple[str, dict, float | None]], top_n: int) -> List[RerankItem]:
    """
    candidates: [(text, metadata, vector_score), ...]
    """
    if not candidates:
        return []

    reranker = get_bge_reranker()

    passages = [c[0] for c in candidates]
    pairs = [[query, p] for p in passages]

    scores = reranker.compute_score(pairs)  # 获取分数

    if isinstance(scores, (float, int)):
        scores = [float(scores)]

    items: List[RerankItem] = []
    for (text, meta, vscore), s in zip(candidates, scores):
        items.append(
            RerankItem(
                text=text,
                metadata=meta or {},
                vector_score=vscore,
                rerank_score=float(s)
            )
        )

    items.sort(key=lambda x: x.rerank_score, reverse=True)
    return items[:top_n]