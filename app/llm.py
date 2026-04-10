from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import OPENAI_API_KEY, OPENAI_MODEL, EMBEDDING_MODEL


def get_llm() -> ChatOpenAI:
    return ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(api_key=OPENAI_API_KEY, model=EMBEDDING_MODEL)
