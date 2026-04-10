from typing import Any, Dict
from app.retriever import search_policies
from app.logger import logger

def search_policy_knowledge(query: str) -> Dict[str, Any]:
    logger.info("Calling RAG tool")
    docs = search_policies(query, k=4)
    logger.info(f"Query: {query}")
    logger.info(f"Top docs retrieved: {len(docs)}")
    return {"documents": docs}
