from llama_index.core import Settings
from llama_index.llms.ollama import Ollama

# 配置 LLM（ Ollama）
Settings.llm = Ollama(
    model="qwen2.5:7b",
    base_url="http://127.0.0.1:11434",
    request_timeout=600.0   # 超时时间，请求最多等 600 秒
)


def demo_simple_chat():
    print("演示：简单对话")
    user_q1 = input("请输入你的问题：").strip()
    if not user_q1:
        print("你没有输入问题。")
        return

    response = Settings.llm.complete(user_q1)
    print("回答：", response.text)


if __name__ == "__main__":
    demo_simple_chat()
