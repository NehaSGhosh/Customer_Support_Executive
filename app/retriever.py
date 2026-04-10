from pathlib import Path
from typing import Dict, List

from langchain_community.vectorstores import FAISS

from app.config import FAISS_DIR, TOP_K
from app.llm import get_embeddings
from app.logger import logger


class PolicySearchError(Exception):
    """Raised when policy retrieval fails."""


_VECTOR_STORE = None


def _load_store() -> FAISS:
    global _VECTOR_STORE

    if _VECTOR_STORE is not None:
        return _VECTOR_STORE

    index_path = Path(FAISS_DIR)
    if not index_path.exists():
        logger.error("FAISS index directory does not exist: %s", index_path)
        raise PolicySearchError("Policy index is not available.")

    try:
        _VECTOR_STORE = FAISS.load_local(
            str(index_path),
            get_embeddings(),
            allow_dangerous_deserialization=True,
        )
        return _VECTOR_STORE
    except Exception as exc:
        logger.exception("Failed to load FAISS vector store")
        raise PolicySearchError("Unable to load the policy search index.") from exc

def search_policies(query: str) -> List[Dict]:
    logger.info("Searching policies")
    logger.debug("Policy query=%s | k=%s", query, TOP_K)

    if not query or not query.strip():
        logger.warning("Empty policy search query received")
        return []

    try:
        store = _load_store()
        docs = store.similarity_search(query, k=TOP_K)
        return [
            {
                "content": d.page_content,
                "metadata": d.metadata,
            }
            for d in docs
        ]
    except PolicySearchError:
        raise
    except Exception as exc:
        logger.exception("Policy vector lookup failed")
        raise PolicySearchError("Policy lookup failed during similarity search.") from exc