from typing import Any, Dict
from app.llm import get_llm


def synthesize_answer(query: str, intent: str, sql_result: Dict[str, Any], policy_result: Dict[str, Any]) -> str:
    llm = get_llm()
    latest_ticket = None
    latest_order = None
    if sql_result.get("tickets"):
        latest_ticket = sql_result["tickets"][0]

    if sql_result.get("orders"):
        latest_order = sql_result["orders"][0]
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
    return llm.invoke(prompt).content
