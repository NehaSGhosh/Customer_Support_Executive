from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import OPENAI_API_KEY, OPENAI_MODEL, EMBEDDING_MODEL, LLM_MAX_RETRIES, LLM_RETRY_BASE_DELAY_SECONDS
import time
from app.logger import logger

TRANSIENT_ERROR_TOKENS = (
    "rate_limit",
    "429",
    "timeout",
    "temporarily unavailable",
    "api_connection",
    "service unavailable",
)

def get_llm() -> ChatOpenAI:
    return ChatOpenAI(api_key=OPENAI_API_KEY, model=OPENAI_MODEL, temperature=0)


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(api_key=OPENAI_API_KEY, model=EMBEDDING_MODEL)

def safe_llm_call(fn):
    last_error = None

    for attempt in range(LLM_MAX_RETRIES):
        try:
            return fn()
        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()
            is_transient = any(token in error_text for token in TRANSIENT_ERROR_TOKENS)

            if not is_transient:
                logger.exception("Non-retryable LLM error")
                raise

            sleep_seconds = LLM_RETRY_BASE_DELAY_SECONDS * (2 ** attempt)
            logger.warning(
                "Transient LLM error on attempt %s/%s. Retrying in %s second(s). Error=%s",
                attempt + 1,
                LLM_MAX_RETRIES,
                sleep_seconds,
                exc,
            )
            time.sleep(sleep_seconds)

    logger.exception("LLM failed after retries")
    raise Exception("LLM failed after retries") from last_error