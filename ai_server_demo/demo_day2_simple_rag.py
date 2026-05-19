"""
第二次课 Demo：
1. 自动读取同级 PDF：肺癌早期诊断的研究进展.pdf
2. 自动解析并写入 PGVector
3. 展示数据库内容
4. 执行一次最简单 RAG 问答
5. 最后自动清空数据库与知识库目录（不留痕迹）
"""

import os
import psycopg2

from config import config
from parser_utils import extract_documents_from_file
from rag_core import ingest_documents, get_llama_retriever
from db_operations import reset_all_data

from llama_index.core import Settings
from llama_index.llms.ollama import Ollama


# ===============================
# 【在本文件内单独配置 LLM】
# ===============================
Settings.llm = Ollama(
    model="qwen2.5:7b",
    base_url="http://127.0.0.1:11434",
    request_timeout=600.0       # 请求超时时间（秒）
)

# 固定文件名
DEMO_FILE_NAME = "肺癌早期诊断的研究进展.pdf"
KNOWLEDGE_BASE_DIR = "knowledge_base"


def step0_ingest_local_demo_file():
    """
    第0步：自动读取本地同级 PDF，解析并入库
    """
    print("=" * 60)
    print("【第0步】自动读取同级文件并入库")
    print("=" * 60)

    # 获取当前脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # 拼接路径
    file_path = os.path.join(script_dir, DEMO_FILE_NAME)

    if not os.path.exists(file_path):
        print(f"❌ 未找到文件：{file_path}")
        print("请把 PDF 放在与 demo_day2_simple_rag.py 同级目录。")
        return False

    print(f"📄 发现文件：{file_path}")
    print("🔍 正在解析文档（含 OCR 逻辑）...")

    # 调用解析器，把 PDF 转成 Document 列表，提取文本内容
    documents = extract_documents_from_file(file_path)
    if not documents:
        print("❌ 文档解析失败：未提取到有效文本")
        return False

    print("📦 正在向量化并写入 PGVector...")
    ingest_documents(documents)
    print("✅ 入库完成")
    return True


def step1_visualize_database():
    """
    第一步：数据库可视化
    """
    print("=" * 60)
    print("【第一步】探秘 PGVector 数据库：看看我们的知识长什么样？")
    print("=" * 60)

    # LlamaIndex 实际向量表名（带 data_ 前缀）
    table_name = f"data_{config.TABLE_NAME}"

    try:
        # 使用配置连接 PostgreSQL
        conn = psycopg2.connect(**config.DB_CONFIG)
        # 创建游标对象用于执行 SQL
        cur = conn.cursor()
        # 查询向量表总记录数
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        # 取查询结果第一列
        count = cur.fetchone()[0]
        print(f"📦 当前数据库中共有 {count} 个知识切片 (Chunks)\n")

        if count == 0:
            print("❗ 数据库为空，请检查入库步骤")
            return

        # 抽样查询最新一条向量记录
        cur.execute(f"""
            SELECT text, metadata_, embedding
            FROM {table_name}
            ORDER BY id DESC
            LIMIT 1
        """)
        # 获取该条记录
        row = cur.fetchone()
        # 拆包字段：文本、元数据、向量
        text, metadata, embedding = row

        print("🔍【抽样查看最新的一条知识切片】")
        print(f"📄 来源文件: {metadata.get('file_name', '未知')}")
        print(f"✂️  切片内容（前 100 字）:\n{text[:100]}...\n")

        # vector 类型在 psycopg2 下可能是字符串或列表，这里兼容处理
        vector_preview = eval(embedding)[:5] if isinstance(embedding, str) else embedding[:5]
        print(f"🔢 向量维度: {config.VECTOR_DIMENSION}")
        print(f"🔢 向量前 5 维: {vector_preview} ...")

    except Exception as e:
        print(f"❌ 数据库连接或查询失败: {e}")
    finally:
        try:
            cur.close()
            conn.close()
        except:
            pass


def step2_simple_rag_chat(query: str):
    """
    第二步： RAG 对话
    """
    print("\n" + "=" * 60)
    print("【第二步】极简 RAG 对话测试")
    print(f"🙋 用户问题: {query}")
    print("=" * 60)

    print("🔎 正在向量数据库中检索相关知识...")
    # 创建检索器，取 Top-3，检索时最多返回 3 条和问题最相关的知识切片
    retriever = get_llama_retriever(similarity_top_k=3)
    # 执行语义检索
    nodes = retriever.retrieve(query)

    if not nodes:
        print("❌ 没有检索到任何相关知识")
        return

    print("\n✅ 检索到以下参考资料：")
    # 初始化本地上下文字符串
    local_context = ""
    for i, node in enumerate(nodes):
        score = node.score or 0.0   # 相似度分数
        file_name = node.metadata.get("file_name", "未知文件")
        print(f"  [{i + 1}] 相似度: {score:.4f} | 来源: {file_name}")
        local_context += node.text + "\n\n"  # 拼接到上下文，供大模型回答使用

    prompt = f"""
    你是一个智能助手。
    请根据以下【参考资料】回答用户问题。
    如果资料中没有答案，请回答“我不知道”。
    
    【参考资料】：
    {local_context}
    
    【用户问题】：
    {query}
    
    请作答：
    """

    print("\n🧠 正在调用大模型（Ollama / qwen2.5:7b）...\n")
    # 调用大模型生成回答
    response = Settings.llm.complete(prompt)

    print("🤖 大模型回答：")
    print(response.text)
    print("\n" + "=" * 60)


def step3_cleanup():
    """
    第三步：演示后自动清理（不留痕迹）
    - 清空向量表
    - 清空语义缓存表
    - 清空 knowledge_base 目录
    """
    print("\n" + "=" * 60)
    print("【第三步】演示结束，自动清理环境")
    print("=" * 60)
    try:
        reset_all_data(KNOWLEDGE_BASE_DIR)
        print("✅ 已清空数据库与知识库目录，环境已复原")
    except Exception as e:
        print(f"❌ 清理失败: {e}")


if __name__ == "__main__":
    try:
        ok = step0_ingest_local_demo_file()
        if not ok:
            raise RuntimeError("自动入库失败，演示终止。")

        step1_visualize_database()

        test_query = input("\n请输入你的测试问题（直接回车使用默认问题）：").strip()
        if not test_query:
            test_query = "文档中提到的肺癌早期诊断方法有哪些？"

        step2_simple_rag_chat(test_query)

    finally:
        # 无论成功或失败，最后都清理，保证教学环境统一
        step3_cleanup()