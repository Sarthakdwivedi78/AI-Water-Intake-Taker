# memory.py — Conversation memory (future use)
# You can extend this to store chat history using LangChain memory modules.

from langchain.memory import ConversationBufferMemory

def get_memory():
    return ConversationBufferMemory(memory_key="chat_history", return_messages=True)
