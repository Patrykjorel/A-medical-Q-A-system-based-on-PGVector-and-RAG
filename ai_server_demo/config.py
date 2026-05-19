class Config:
    # 数据库配置
    DB_CONFIG = {
        "dbname": "domain_knowledge_db",
        "user": "postgres",
        "password": "123456",  # 请替换为真实密码
        "host": "localhost",
        "port": "5432"
    }

    # 向量存储的维度
    VECTOR_DIMENSION = 384

    # 知识库索引表名
    TABLE_NAME = "knowledge_llama_index"

    # Embedding 模型配置
    EMBEDDING_MODEL_PATH = "models/bge-base-zh-v1.5"

    # LLM 配置
    LLM_HOST = "http://127.0.0.1:11434"
    LLM_MODEL = "qwen2.5:7b"

    # 模型回答语言："en" 默认英文；"zh" 默认中文（仅影响 rag_core 主 Prompt）
    DEFAULT_RESPONSE_LANGUAGE = "en"

    # 检索器配置
    RETRIEVER_TOP_K = 30  # 第一阶段：向量召回候选数
    RERANK_TOP_N = 5  # 第二阶段：重排后返回数
    SIMILARITY_THRESHOLD = 0.6

    # 文件解析与拆分配置
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 100

    # 语义缓存配置
    SEMANTIC_CACHE_TABLE = "semantic_cache"
    SEMANTIC_CACHE_THRESHOLD = 0.92  # 余弦相似度阈值，越高越严格

    # ========== Reranker（BGE）配置 ==========
    ENABLE_RERANKER = True
    # GPU 推荐：BAAI/bge-reranker-v2-m3（精度高、支持更长文本）
    # CPU 推荐：BAAI/bge-reranker-base（更快）
    RERANKER_MODEL_NAME = "models/bge-reranker-v2-m3"
    RERANK_USE_FP16 = True  # 有 GPU 再开；纯 CPU 建议 False

    # 百度 OCR API 配置
    # 请前往 https://console.bce.baidu.com/ 申请
    OCR_TEXT_LEN_THRESHOLD = 20
    OCR_ON_IMAGE_PAGES = True   # 如果一个页面有图片就开启OCR识别
    BAIDU_OCR_APP_ID = "122276603"  # 替换为你的 APP_ID
    BAIDU_OCR_API_KEY = "VTBSzLXqK3bFo6nzUIllZJnm"  # 替换为你的 API_KEY
    BAIDU_OCR_SECRET_KEY = "cl1D92sWzryPxNR9RkpK5JQnjOIOcgFw"  # 替换为你的 SECRET_KEY

    # ========== 阿里云 AI搜索开放平台 配置（联网搜索） ==========
    ALIYUN_SEARCH_HOST = "http://default-1o7y.platform-cn-shanghai.opensearch.aliyuncs.com"
    ALIYUN_SEARCH_API_KEY = "OS-c917u8tsi679zl9v"  # 替换为你的真实 API-KEY
    ALIYUN_SEARCH_WORKSPACE = "default"  # 工作空间名称
    ALIYUN_SEARCH_SERVICE_ID = "ops-web-search-001"  # 联网搜索服务ID
    ALIYUN_SEARCH_TOP_K = 5  # 搜索返回结果数
    ALIYUN_SEARCH_CONTENT_TYPE = "snippet"  # snippet 返回网页内容的简短摘要（几句话） 或 summary 返回网页内容的详细文本摘要（段落级别）

    # 构建数据库连接URI
    @classmethod
    def get_postgres_uri(cls):
        user = cls.DB_CONFIG["user"]
        password = cls.DB_CONFIG["password"]
        host = cls.DB_CONFIG["host"]
        port = cls.DB_CONFIG["port"]
        dbname = cls.DB_CONFIG["dbname"]
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


config = Config()