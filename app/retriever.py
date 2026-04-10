from typing import Dict, List
from langchain_community.vectorstores import FAISS
from app.config import FAISS_DIR
from app.llm import get_embeddings
from app.logger import logger

def search_policies(query: str, k: int = 4) -> List[Dict]:
    logger.info("Searching policies")
    logger.debug(f"Query: {query} and k: {k}")
    store = FAISS.load_local(str(FAISS_DIR), get_embeddings(), allow_dangerous_deserialization=True)
    docs = store.similarity_search(query, k=k)
    return [
        {
            "content": d.page_content,
            "metadata": d.metadata,
        }
        for d in docs
    ]
