import os
import shutil
import psycopg2
from config import config


def _safe_filename(file_name: str) -> str:
    if not file_name:
        raise ValueError("file_name 不能为空")
    normalized = os.path.basename(file_name)
    if normalized != file_name or "/" in file_name or "\\" in file_name:
        raise ValueError("非法文件名")
    return normalized


def delete_knowledge_file(file_name: str, knowledge_base_dir: str = "knowledge_base") -> dict:
    safe_name = _safe_filename(file_name)

    # 1) 删除知识库目录中的实际文件（与 upload 路径保持一致）
    candidate_paths = [
        os.path.join(knowledge_base_dir, "pdf", safe_name),
        os.path.join(knowledge_base_dir, "txt", safe_name),
        os.path.join(knowledge_base_dir, "word", safe_name),
        os.path.join(knowledge_base_dir, safe_name),  # 兜底
    ]

    deleted_paths = []
    for path in candidate_paths:
        if os.path.exists(path):
            os.remove(path)
            deleted_paths.append(path)

    file_deleted = len(deleted_paths) > 0

    # 2) 删除向量库中该文件相关的向量
    actual_table = f"data_{config.TABLE_NAME}"
    conn = None
    deleted_vectors = 0
    try:
        conn = psycopg2.connect(**config.DB_CONFIG)
        with conn.cursor() as cur:
            cur.execute(f"""
                DELETE FROM {actual_table}
                WHERE metadata_ ->> 'file_name' = %s
                   OR metadata_ ->> 'source' LIKE %s
                   OR metadata_ ->> 'source' LIKE %s
                   OR metadata_ ->> 'source' LIKE %s
            """, (
                safe_name,
                f"%/{safe_name}",   # Linux/macOS 路径
                f"%\\{safe_name}",  # Windows 路径
                f"%{safe_name}%",   # 兜底匹配
            ))
            deleted_vectors = cur.rowcount
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

    return {
        "file_name": safe_name,
        "file_deleted": file_deleted,
        "deleted_vectors": deleted_vectors,
        "deleted_paths": deleted_paths
    }


def reset_all_data(knowledge_base_dir: str):
    """清空向量表、语义缓存表、知识库文件"""
    actual_table = f"data_{config.TABLE_NAME}"
    cache_table = config.SEMANTIC_CACHE_TABLE

    conn = psycopg2.connect(**config.DB_CONFIG)  # 连接数据库
    cur = conn.cursor()  # 执行 SQL 的操作句柄

    # 清空向量表
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        );
    """, (actual_table,))
    if cur.fetchone()[0]:
        cur.execute(f"TRUNCATE TABLE {actual_table} CASCADE;")
        print(f"已清空向量知识库表: {actual_table}")

    # 清空语义缓存表
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = %s
        );
    """, (cache_table,))
    if cur.fetchone()[0]:
        cur.execute(f"TRUNCATE TABLE {cache_table} CASCADE;")
        print(f"已清空语义缓存表: {cache_table}")

    conn.commit()
    cur.close()
    conn.close()

    # 清空知识库文件
    if os.path.exists(knowledge_base_dir):
        shutil.rmtree(knowledge_base_dir)
        os.makedirs(os.path.join(knowledge_base_dir, "pdf"), exist_ok=True)
        os.makedirs(os.path.join(knowledge_base_dir, "word"), exist_ok=True)
        os.makedirs(os.path.join(knowledge_base_dir, "txt"), exist_ok=True)
        print("已清空知识库文件目录")