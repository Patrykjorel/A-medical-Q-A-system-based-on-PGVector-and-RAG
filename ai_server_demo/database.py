from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy import make_url
from config import config


def get_pgvector_store() -> PGVectorStore:
    """
    构建并返回 PGVectorStore，作为向量库入口。
    """
    db_config = config.DB_CONFIG   # 读取数据库连接参数

    # 组装连接参数
    vector_store = PGVectorStore.from_params(
        database=db_config["dbname"],        # PostgreSQL 数据库名
        host=db_config["host"],              # 主机地址
        password=db_config["password"],      # 密码
        port=db_config["port"],              # 端口
        user=db_config["user"],              # 用户名
        table_name=config.TABLE_NAME,        # 向量表逻辑名（最终会生成 data_前缀表）
        embed_dim=config.VECTOR_DIMENSION    # 向量维度，必须与 embedding 模型输出一致（384）
    )
    return vector_store