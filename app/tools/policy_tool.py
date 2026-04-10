from typing import Any, Dict

from app.logger import logger
from app.retriever import PolicySearchError, search_policies


def search_policy_knowledge(query: str) -> Dict[str, Any]:
    logger.info("Calling RAG tool")
    logger.info("Policy search query: %s", query)

    try:
        docs = search_policies(query)
        logger.info("Top docs retrieved: %s", len(docs))
        return {
            "documents": docs,
            "error": None,
        }
    except PolicySearchError as exc:
        logger.warning("Policy search unavailable: %s", exc)
        return {
            "documents": [],
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception("Unexpected policy tool failure")
        return {
            "documents": [],
            "error": "Policy search is temporarily unavailable.",
        }