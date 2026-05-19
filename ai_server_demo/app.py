from flask import Flask
from flask_cors import CORS
import os
import re
from db_operations import delete_knowledge_file, reset_all_data

from flask import request, jsonify
from parser_utils import extract_documents_from_file
from rag_core import ingest_documents, build_llamaindex_rag_chain
from semantic_cache import search_cache, save_to_cache, get_cache_stats
from urllib.parse import unquote

app = Flask(__name__)
CORS(app)

# 知识库目录和临时文件目录
KNOWLEDGE_BASE_DIR = "knowledge_base"
TEMP_DIR = "temp"

os.makedirs(os.path.join(KNOWLEDGE_BASE_DIR, "pdf"), exist_ok=True)
os.makedirs(os.path.join(KNOWLEDGE_BASE_DIR, "word"), exist_ok=True)
os.makedirs(os.path.join(KNOWLEDGE_BASE_DIR, "txt"), exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)


def split_think_answer(raw_text: str):
    """
    将模型输出拆成 think 与 answer 两部分，便于前端分开展示。
    目的：
    1) 控制前端是否显示思考过程
    2) 兼容旧缓存中混有 <think> 标签的答案
    """
    text = (raw_text or "").strip()
    if not text:
        return "", ""

    # 标准 <think>...</think>
    pattern = re.compile(r"<think>([\s\S]*?)</think>", re.IGNORECASE)
    think_parts = [m.strip() for m in pattern.findall(text) if m.strip()]
    answer = pattern.sub("", text).strip()

    if think_parts:
        return "\n\n".join(think_parts), answer

    # 兜底：只有 <think> 没有闭合
    m = re.search(r"<think>", text, re.IGNORECASE)
    if m:
        idx = m.start()
        return text[idx + len("<think>"):].strip(), text[:idx].strip()

    return "", text


@app.route('/api/ask', methods=['POST'])
def ask_question():
    """
    问答主接口：
    - 读取参数：question/use_search/use_cache/selected_knowledge_bases/history
    - 命中语义缓存（仅限 use_search=False）
    - 执行 RAG 主链路生成答案
    - 拆分 think/answer，统一返回结构

    接收参数：
    - question: 用户问题
    - use_search: 是否启用联网搜索
    - use_cache: 是否启用语义缓存
    - selected_knowledge_bases: 选中的知识库文件列表
    """
    data = request.json
    # 当前问题
    question = data.get('question')
    # 是否联网搜索
    use_search = data.get('use_search', False)
    # 是否启用语义缓存
    use_cache = data.get('use_cache', True)
    # 指定知识库文件过滤
    selected_knowledge_bases = data.get('selected_knowledge_bases', [])
    # 多轮对话历史
    chat_history = data.get('history', [])
    if not question:
        return jsonify({"code": 400, "msg": "问题不能为空", "data": None}), 400
    try:
        # 缓存只在“纯本地检索模式”使用，避免联网结果时效性问题污染缓存
        if use_cache and not use_search:
            cache_result = search_cache(question, use_search=use_search)
            if cache_result:
                cached_answer = cache_result.get("answer", "")
                # 兼容旧缓存里可能混有<think>
                _, clean_answer = split_think_answer(cached_answer)
                return jsonify({
                    "code": 200, "msg": "success",
                    "data": {
                        "answer": clean_answer,
                        "think": "",  # 缓存一般不返回思考过程
                        "source": "cache"
                    }
                })
        # 调用 RAG 主链路，chat_history 参数传入
        raw_answer, source = build_llamaindex_rag_chain(
            question,
            use_search=use_search,
            selected_files=selected_knowledge_bases,
            history=chat_history
        )
        # 拆分 think 和最终回答（前端展示控制）
        think, final_answer = split_think_answer(raw_answer)
        if not final_answer:
            final_answer = "根据现有资料，我无法确定该问题的答案。"

        # 只缓存 final_answer，不缓存 think，避免缓存污染
        if use_cache and not use_search:
            # 只缓存最终答案，避免缓存污染
            save_to_cache(question, final_answer, source=source, use_search=use_search)

        # 统一返回结构：answer/think/source
        return jsonify({
            "code": 200, "msg": "success",
            "data": {
                "answer": final_answer,
                "think": think,
                "source": source
            }
        })
    except Exception as e:
        print(f"RAG Generate Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"code": 500, "msg": f"生成回答时发生错误: {str(e)}", "data": None}), 500


@app.route("/api/delete_file", methods=["DELETE"])
def api_delete_file():
    """
        删除知识库文件接口
        在 RAG 系统中，所谓的"删除"必须是一个“双重删除”操作（原子性）：
        1. 删除物理硬盘上的真实文件（PDF/Word/TXT 等）
        2. 删除 PGVector 向量数据库中，由该文件拆分产生的所有 Vector 向量切片数据
        如果不删除向量数据，库里就会残留“幽灵知识”，导致 AI 依然能根据已删除的文件回答问题。
    """
    # === 阶段 1：获取与清洗前端参数 ===
    raw_name = (request.args.get("file_name") or "").strip()

    # 【细节处理】：兼容 1~2 次 URL 编码
    # 前端框架（如 axios/vue-router）在传递中文字符（如"前端白皮书.pdf"）时，
    # 常常会发生 URL 编码（%E5%89%8D...）。这里通过循环解码，还原真实的中文文件名。
    file_name = raw_name
    for _ in range(2):
        decoded = unquote(file_name)
        if decoded == file_name:
            break
        file_name = decoded

    # === 阶段 2：参数前置校验 ===
    if not file_name:
        return jsonify({"code": 400, "msg": "file_name 不能为空", "data": None})

    try:
        # === 阶段 3：执行核心双切删除逻辑 ===
        # 调用底层 db_operations 中的 delete_knowledge_file 函数
        # 该函数内部会：找到目标目录删除文件实体 -> 并在 PGVector 表中执行 DELETE WHERE file_name = xxx
        data = delete_knowledge_file(file_name, KNOWLEDGE_BASE_DIR)

        # === 阶段 4：处理各类返回状态 ===
        # 情况 A：如果硬盘文件没找到，且数据库里受影响的向量行数也是 0，说明文件本来就不存在
        if (not data["file_deleted"]) and data["deleted_vectors"] == 0:
            return jsonify({
                "code": 404,
                "msg": "文件不存在或已被删除",
                "data": data
            })
        # 情况 B：正常删除成功。返回删除了哪个文件，以及清理了多少条数据库向量切片
        return jsonify({
            "code": 200,
            "msg": "删除成功",
            "data": data
        })
    except ValueError as e:
        return jsonify({
            "code": 400,
            "msg": str(e),
            "data": None
        })
    except Exception as e:
        return jsonify({
            "code": 500,
            "msg": f"删除失败: {e}",
            "data": None
        })


@app.route('/api/reset', methods=['POST'])
def reset_database():
    """重置数据库接口"""
    try:
        reset_all_data(KNOWLEDGE_BASE_DIR)
        return jsonify({
            "code": 200,
            "msg": "数据库重置成功",
            "data": {"status": "success"}
        })
    except Exception as e:
        print(f"重置数据库失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"code": 500, "msg": f"重置失败: {str(e)}"}), 500


# 上传并解析文档
@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件接口"""
    if 'file' not in request.files:
        return jsonify({"code": 400, "msg": "未找到文件"}), 400

    # 1) 获取前端上传文件对象（multipart/form-data）
    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": 400, "msg": "文件名为空"}), 400

    # 2) 校验扩展名是否在白名单内，避免不支持格式进入解析链路
    file_ext = os.path.splitext(file.filename)[1].lower()
    allowed_extensions = ['.pdf', '.txt', '.md']
    if file_ext not in allowed_extensions:
        return jsonify({
            "code": 400,
            "msg": f"不支持的文件类型: {file_ext}，仅支持 {', '.join(allowed_extensions)}"
        }), 400

    # 3) 将原始上传文件先落到 temp 目录，供解析器读取
    # 第一：上传流先落盘，解析器更稳定
    # 很多解析库（PDF / OCR）更适合接收“文件路径”，不是内存流。
    # 第二：失败隔离
    # 先存temp /，解析失败不会污染正式知识库目录（knowledge_base /）
    # upload -> temp保存 -> 解析+入库成功 -> move到knowledge_base
    temp_path = os.path.join(TEMP_DIR, file.filename)
    file.save(temp_path)

    try:
        # 4) 调用解析模块：把文件转为统一的 Document 列表（含 OCR 兜底）
        print(f"开始解析文件: {file.filename}")
        documents = extract_documents_from_file(temp_path)

        if not documents:
            return jsonify({"code": 400, "msg": "未能从文件中提取到任何文字内容"}), 400

        # PDF所有的文件内容提取
        # 5) 核心入库：切分 -> 向量化 -> 写入 PGVector
        print(f"开始将文档向量化并存入知识库...")
        ingest_documents(documents)

        # 根据扩展名决定知识库文件存储目录
        if file_ext == '.pdf':
            target_dir = os.path.join(KNOWLEDGE_BASE_DIR, "pdf")
        elif file_ext in ['.txt', '.md']:
            target_dir = os.path.join(KNOWLEDGE_BASE_DIR, "txt")
        else:
            target_dir = KNOWLEDGE_BASE_DIR

        # 目标文件路径
        target_path = os.path.join(target_dir, file.filename)

        # 同名冲突处理：加时间戳避免覆盖
        if os.path.exists(target_path):
            import time
            timestamp = int(time.time())
            name, ext = os.path.splitext(file.filename)
            target_path = os.path.join(target_dir, f"{name}_{timestamp}{ext}")

        os.rename(temp_path, target_path) # 将 temp 文件移动到 knowledge_base 对应目录
        print(f"文件已保存到: {target_path}")

        return jsonify({
            "code": 200,
            "msg": "知识库更新成功",
            "data": {
                "filename": file.filename,
                "saved_path": target_path
            }
        })

    except Exception as e:
        print(f"文件处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"code": 500, "msg": f"文件处理失败: {str(e)}"}), 500
    # finally 做兜底清理：避免 temp 垃圾文件残留
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass


@app.route('/api/list_files', methods=['GET'])
def list_files():
    """列出知识库中的所有文件"""
    try:
        files = {"pdf": [], "txt": [], "word": []}
        for category in files.keys():
            dir_path = os.path.join(KNOWLEDGE_BASE_DIR, category)
            if os.path.exists(dir_path):
                files[category] = os.listdir(dir_path)

        return jsonify({"code": 200, "msg": "success", "data": files})
    except Exception as e:
        return jsonify({"code": 500, "msg": f"获取文件列表失败: {str(e)}"}), 500


@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    """获取语义缓存统计信息"""
    stats = get_cache_stats()
    return jsonify({"code": 200, "msg": "success", "data": stats})


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "code": 200,
        "msg": "服务运行正常",
        "data": {"status": "healthy", "version": "2.0.0"}
    })


if __name__ == '__main__':
    print("=" * 60)
    print("RAG API 服务器正在启动（已启用语义缓存）...")
    print(f"知识库目录: {os.path.abspath(KNOWLEDGE_BASE_DIR)}")
    print(f"临时文件目录: {os.path.abspath(TEMP_DIR)}")
    print("默认监听端口: 5000")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5000, debug=False)