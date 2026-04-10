from typing import Literal
from langgraph.graph import END, START, StateGraph

from app.state import AgentState
from app.mcp_client import call_tool
from app.tools.response_tool import synthesize_answer
from app.logger import logger
from app.llm import safe_llm_call, get_llm

def classify_intent(query: str) -> str:
    llm = get_llm()
    prompt = f"""
Classify the user query into exactly one of these labels:

- structured:
  Queries about customer data, ticket, order, account, profile, complaint, or support history.
  These are fulfilled entirely using database (SQL) data.

- document:
  Queries about policies, such as refund policy, privacy policy, cancellation, return policy, or terms.

- hybrid:
  ONLY if the query requires BOTH:
  1) customer/order/ticket data AND
  2) policy/document reasoning

  Example:
  - "Does Rachel Moore's complaint qualify for a refund?" → hybrid

IMPORTANT RULES:
- Asking for profile, tickets, or orders together is STILL structured
- Multiple structured data types do NOT make it hybrid
- Only choose hybrid if policy or document reasoning is explicitly required

- clarify:
  If the query is vague or unclear

Return only one label.

Query: {query}
"""
    response = safe_llm_call(lambda: llm.invoke(prompt)).content.strip().lower()

    allowed = {"structured", "document", "hybrid", "clarify"}
    if response not in allowed:
        return "clarify"
    return response


class SupportMultiAgent:
    def __init__(self) -> None:
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(AgentState)

        graph.add_node("route", self.route)
        graph.add_node("clarify", self.clarify)
        graph.add_node("sql_agent", self.sql_agent)
        graph.add_node("policy_agent", self.policy_agent)
        graph.add_node("answer", self.answer)

        graph.add_edge(START, "route")

        graph.add_conditional_edges(
            "route",
            self.next_step,
            {
                "sql_agent": "sql_agent",
                "policy_agent": "policy_agent",
                "hybrid_sql": "sql_agent",
                "clarify": "clarify",
            },
        )

        graph.add_conditional_edges(
            "sql_agent",
            self.after_sql,
            {
                "policy_agent": "policy_agent",
                "answer": "answer",
            },
        )

        graph.add_edge("policy_agent", "answer")
        graph.add_edge("clarify", END)
        graph.add_edge("answer", END)

        return graph.compile()

    def route(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | route")
        query = state["query"]
        intent = classify_intent(query)

        logger.info(f"ROUTE_DECISION | intent={intent}")

        return {
            **state,
            "intent": intent,
            "tools_called": list(state.get("tools_called", [])),
        }

    def next_step(
        self, state: AgentState
    ) -> Literal["sql_agent", "policy_agent", "hybrid_sql", "clarify"]:
        intent = state["intent"]
        logger.info(f"ROUTER | next_step | intent={intent}")

        if intent == "structured":
            next_node = "sql_agent"
        elif intent == "hybrid":
            next_node = "hybrid_sql"
        elif intent == "document":
            next_node = "policy_agent"
        else:
            next_node = "clarify"

        logger.info(f"ROUTER_DECISION | next_node={next_node}")
        return next_node

    def sql_agent(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | sql_agent")
        logger.info("TOOL_CALL | mcp.sql_lookup")

        try:
            result = call_tool("sql_lookup", {"query": state["query"]})
        except Exception as exc:
            logger.exception("TOOL_ERROR | mcp.sql_lookup failed")
            result = {"error": f"sql_lookup failed: {str(exc)}"}

        tools = list(state.get("tools_called", [])) + ["mcp.sql_lookup"]

        return {
            **state,
            "sql_result": result,
            "tools_called": tools,
        }

    def after_sql(self, state: AgentState) -> Literal["policy_agent", "answer"]:
        logger.info(f"ROUTER | after_sql | intent={state['intent']}")

        if state["intent"] == "hybrid":
            next_node = "policy_agent"
        else:
            next_node = "answer"

        logger.info(f"ROUTER_DECISION | next_node={next_node}")
        return next_node

    def policy_agent(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | policy_agent")
        logger.info("TOOL_CALL | mcp.policy_search")

        try:
            result = call_tool("policy_search", {"query": state["query"]})
        except Exception as exc:
            logger.exception("TOOL_ERROR | mcp.policy_search failed")
            result = {"error": f"policy_search failed: {str(exc)}"}

        tools = list(state.get("tools_called", [])) + ["mcp.policy_search"]

        logger.debug(f"TOOL_RESULT | mcp.policy_search | preview={str(result)[:300]}")

        return {
            **state,
            "policy_result": result,
            "tools_called": tools,
        }

    def clarify(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | clarify")

        follow_up = (
            "I want to make sure I understand your request correctly. Please clarify a bit more.\n\n"
            "Are you asking about customer/order data, policy documents, or both? "
            "For example, you can ask:\n"
            "- 'Show Michael's profile and past tickets'\n"
            "- 'What is the refund policy?'\n"
            "- 'Does Rachel’s recent complaint qualify for refund?'"
        )

        logger.info("NODE_END | clarify")

        return {
            **state,
            "final_answer": follow_up,
        }

    def answer(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | answer")
        logger.debug(f"ANSWER_INPUT | sql_result={state.get('sql_result', {})}")
        logger.debug(f"ANSWER_INPUT | policy_result={state.get('policy_result', {})}")


        text = synthesize_answer(
            query=state["query"],
            sql_result=state.get("sql_result", {}),
            policy_result=state.get("policy_result", {}),
        )

        logger.debug(f"NODE_END | answer | preview={text[:300]}")

        return {
            **state,
            "final_answer": text,
        }

    def run(self, query: str):
        logger.info("===================================================")
        logger.info("GRAPH_START")
        logger.debug(f"USER_QUERY | {query}")

        result = self.graph.invoke({"query": query, "tools_called": []})

        logger.debug(f"GRAPH_END | final_answer={result.get('final_answer', '')[:300]}")
        logger.info("===================================================")

        return result