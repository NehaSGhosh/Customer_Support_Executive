from typing import Any, Dict
from app.llm import get_llm,safe_llm_call

def synthesize_answer(query: str, sql_result: Dict[str, Any], policy_result: Dict[str, Any]) -> str:
    llm = get_llm()
    prompt = f"""
        You are a grounded customer support assistant.

        Use only the provided data.
        Do not use outside knowledge.
        If data is missing, say that clearly.

        User query:
        {query}

        SQL result:
        {sql_result}

        Policy result:
        {policy_result}

        Instructions:
        - For hybrid refund questions, mention the latest relevant ticket details.
        - Mention related order details if present.
        - Mention the policy rule that applies.
        - State whether the complaint qualifies, does not qualify, or cannot be determined.
        - If SQL result contains tickets/orders, include them explicitly in the answer.
        """

    return safe_llm_call(lambda: llm.invoke(prompt)).content
