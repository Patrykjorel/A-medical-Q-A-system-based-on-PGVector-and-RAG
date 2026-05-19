"""
打印与线上 RAG 一致的「检索排序列表」，供 Hit@K / MRR 人工评测。

用法（在 ai_server_demo 目录下，已配置好数据库与知识库）:
  python eval_retrieval.py "阿司匹林的适应症是什么？"
  python eval_retrieval.py "问题" --files file1.pdf,file2.pdf
  python eval_retrieval.py --queries-file queries.txt
  python eval_retrieval.py "问题" --json

依赖: 与主项目相同（需能连 PostgreSQL、加载 embedding / 可选 reranker）。
"""
from __future__ import annotations

import argparse
import json
import sys

from rag_core import get_ranked_chunks_for_eval


def _parse_files(s: str | None) -> list[str] | None:
    if not s or not s.strip():
        return None
    parts = [p.strip() for p in s.split(",") if p.strip()]
    return parts if parts else None


def print_rows(query: str, rows: list[dict], as_json: bool) -> None:
    if as_json:
        print(json.dumps({"query": query, "chunks": rows}, ensure_ascii=False, indent=2))
        return
    print("=" * 72)
    print(f"Query: {query}")
    print(f"Count: {len(rows)}  (stage 与 rag_core.build_llamaindex_rag_chain 本地分支一致)")
    print("=" * 72)
    for r in rows:
        print(f"\n--- rank={r['rank']}  stage={r['stage']}  file={r['file_name']!r}")
        print(f"    node_id={r['node_id']!r}")
        vs = r.get("vector_score")
        rs = r.get("rerank_score")
        print(f"    vector_score={vs}  rerank_score={rs}")
        preview = (r.get("text_preview") or "").replace("\n", " ")
        if len(preview) > 500:
            preview = preview[:500] + "..."
        print(f"    preview: {preview}")


def main() -> int:
    parser = argparse.ArgumentParser(description="导出 RAG 检索排序列表（评测用）")
    parser.add_argument(
        "query",
        nargs="?",
        default=None,
        help="单个测试问题",
    )
    parser.add_argument(
        "--files",
        default=None,
        help="逗号分隔的文件名子串，与前端 selectedKnowledgeBases 一致；不传则全库检索",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        dest="top_k",
        help="向量召回条数，默认使用 config.RETRIEVER_TOP_K",
    )
    parser.add_argument(
        "--preview-chars",
        type=int,
        default=400,
        help="text_preview 最大字符数",
    )
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    parser.add_argument(
        "--queries-file",
        default=None,
        help="每行一个问题的文本文件（UTF-8）",
    )
    args = parser.parse_args()

    selected = _parse_files(args.files)

    queries: list[str] = []
    if args.queries_file:
        with open(args.queries_file, encoding="utf-8") as f:
            queries = [line.strip() for line in f if line.strip()]
    elif args.query:
        queries = [args.query]
    else:
        parser.print_help()
        print("\n错误: 请提供 query 或 --queries-file", file=sys.stderr)
        return 2

    for q in queries:
        rows = get_ranked_chunks_for_eval(
            q,
            selected_files=selected,
            similarity_top_k=args.top_k,
            preview_chars=args.preview_chars,
        )
        print_rows(q, rows, args.json)
        if not args.json and len(queries) > 1:
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
