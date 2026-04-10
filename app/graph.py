from typing import Literal
from langgraph.graph import END, START, StateGraph

from app.state import AgentState
from app.tools.sql_tool import lookup_customer_support_data
from app.tools.policy_tool import search_policy_knowledge
from app.tools.response_tool import synthesize_answer
from app.logger import logger


def classify_intent(query: str) -> str:
    logger.info("NODE_START | classify_intent")
    logger.info(f"STATE_IN | query={query}")

    q = query.lower().strip()

    doc_words = ["policy", "refund", "privacy", "cancellation", "document", "terms", "return"]
    sql_words = [
        "customer", "profile", "ticket", "history", "account", "complaint",
        "order", "status", "email", "phone", "ema", "ravi", "lisa"
    ]

    has_doc = any(w in q for w in doc_words)
    has_sql = any(w in q for w in sql_words)

    if has_doc and has_sql:
        intent = "hybrid"
    elif has_doc:
        intent = "document"
    elif has_sql:
        intent = "structured"
    else:
        intent = "clarify"

    logger.info(f"DECISION | classify_intent -> {intent}")
    return intent


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
        logger.info("TOOL_CALL | sql_lookup")

        result = lookup_customer_support_data(state["query"])
        tools = list(state.get("tools_called", [])) + ["sql_lookup"]

        logger.info(f"TOOL_RESULT | sql_lookup | preview={str(result)[:300]}")

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
        logger.info("TOOL_CALL | policy_search")

        result = search_policy_knowledge(state["query"])
        tools = list(state.get("tools_called", [])) + ["policy_search"]

        logger.info(f"TOOL_RESULT | policy_search | preview={str(result)[:300]}")

        return {
            **state,
            "policy_result": result,
            "tools_called": tools,
        }

    def clarify(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | clarify")

        follow_up = (
            "I’m not fully sure what you want yet. "
            "Are you asking about customer/order data, policy documents, or both? "
            "For example, you can ask:\n"
            "- 'Show Ema’s profile and past tickets'\n"
            "- 'What is the refund policy?'\n"
            "- 'Does Ema’s recent complaint qualify for refund?'"
        )

        logger.info("NODE_END | clarify")

        return {
            **state,
            "final_answer": follow_up,
        }

    def answer(self, state: AgentState) -> AgentState:
        logger.info("NODE_START | answer")
        logger.info(f"ANSWER_INPUT | sql_result={state.get('sql_result', {})}")
        logger.info(f"ANSWER_INPUT | policy_result={state.get('policy_result', {})}")


        text = synthesize_answer(
            query=state["query"],
            intent=state["intent"],
            sql_result=state.get("sql_result", {}),
            policy_result=state.get("policy_result", {}),
        )

        logger.info(f"NODE_END | answer | preview={text[:300]}")

        return {
            **state,
            "final_answer": text,
        }

    def run(self, query: str):
        logger.info("===================================================")
        logger.info("GRAPH_START")
        logger.info(f"USER_QUERY | {query}")

        result = self.graph.invoke({"query": query, "tools_called": []})

        logger.info(f"GRAPH_END | final_answer={result.get('final_answer', '')[:300]}")
        logger.info("===================================================")

        return result