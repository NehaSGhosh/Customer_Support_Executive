from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    query: str
    intent: str
    tools_called: List[str]
    sql_result: Dict[str, Any]
    policy_result: Dict[str, Any]
    final_answer: str
