import app.graph as graph_module


def test_classify_intent_document():
    assert graph_module.classify_intent("What is the refund policy?") == "document"


def test_classify_intent_structured():
    assert graph_module.classify_intent("Show customer Rachel Moore's order history") == "structured"


def test_classify_intent_hybrid():
    q = "Does Rachel Moore's latest complaint qualify for refund under the current policy?"
    assert graph_module.classify_intent(q) == "hybrid"


def test_classify_intent_clarify():
    assert graph_module.classify_intent("Help me with something") == "clarify"


def test_classify_intent_case_and_whitespace_insensitive():
    assert graph_module.classify_intent("   REFUND POLICY   ") == "document"


def test_route_sets_intent_and_preserves_tools_called():
    agent = graph_module.SupportMultiAgent()
    state = {"query": "What is the refund policy?", "tools_called": ["existing.tool"]}

    result = agent.route(state)

    assert result["intent"] == "document"
    assert result["tools_called"] == ["existing.tool"]


def test_next_step_structured():
    agent = graph_module.SupportMultiAgent()
    assert agent.next_step({"intent": "structured"}) == "sql_agent"


def test_next_step_document():
    agent = graph_module.SupportMultiAgent()
    assert agent.next_step({"intent": "document"}) == "policy_agent"


def test_next_step_hybrid():
    agent = graph_module.SupportMultiAgent()
    assert agent.next_step({"intent": "hybrid"}) == "hybrid_sql"


def test_next_step_clarify():
    agent = graph_module.SupportMultiAgent()
    assert agent.next_step({"intent": "clarify"}) == "clarify"


def test_after_sql_hybrid_goes_to_policy_agent():
    agent = graph_module.SupportMultiAgent()
    assert agent.after_sql({"intent": "hybrid"}) == "policy_agent"


def test_after_sql_non_hybrid_goes_to_answer():
    agent = graph_module.SupportMultiAgent()
    assert agent.after_sql({"intent": "structured"}) == "answer"


def test_sql_agent_success(monkeypatch):
    agent = graph_module.SupportMultiAgent()
    monkeypatch.setattr(graph_module, "call_tool", lambda name, args: {"ok": True, "tool": name, "args": args})

    state = {"query": "Show Rachel's profile", "tools_called": []}
    result = agent.sql_agent(state)

    assert result["sql_result"]["ok"] is True
    assert result["tools_called"] == ["mcp.sql_lookup"]


def test_sql_agent_failure(monkeypatch):
    agent = graph_module.SupportMultiAgent()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(graph_module, "call_tool", _boom)
    result = agent.sql_agent({"query": "Show Rachel's profile", "tools_called": []})

    assert "sql_lookup failed: db unavailable" == result["sql_result"]["error"]
    assert result["tools_called"] == ["mcp.sql_lookup"]


def test_policy_agent_success(monkeypatch):
    agent = graph_module.SupportMultiAgent()
    monkeypatch.setattr(graph_module, "call_tool", lambda name, args: {"documents": [{"content": "refunds"}]})

    result = agent.policy_agent({"query": "refund policy", "tools_called": []})

    assert result["policy_result"]["documents"][0]["content"] == "refunds"
    assert result["tools_called"] == ["mcp.policy_search"]


def test_policy_agent_failure(monkeypatch):
    agent = graph_module.SupportMultiAgent()

    def _boom(*_args, **_kwargs):
        raise RuntimeError("faiss missing")

    monkeypatch.setattr(graph_module, "call_tool", _boom)
    result = agent.policy_agent({"query": "refund policy", "tools_called": []})

    assert "policy_search failed: faiss missing" == result["policy_result"]["error"]
    assert result["tools_called"] == ["mcp.policy_search"]


def test_clarify_sets_follow_up_text():
    agent = graph_module.SupportMultiAgent()
    result = agent.clarify({"query": "help"})

    assert "customer/order data" in result["final_answer"]
    assert "refund policy" in result["final_answer"]


def test_answer_calls_synthesize_answer(monkeypatch):
    agent = graph_module.SupportMultiAgent()
    captured = {}

    def fake_synthesize_answer(**kwargs):
        captured.update(kwargs)
        return "final synthesized answer"

    monkeypatch.setattr(graph_module, "synthesize_answer", fake_synthesize_answer)
    state = {
        "query": "Does this qualify for refund?",
        "intent": "hybrid",
        "sql_result": {"tickets": [{"id": 1}]},
        "policy_result": {"documents": [{"content": "Refund within 30 days"}]},
        "tools_called": [],
    }
    result = agent.answer(state)

    assert result["final_answer"] == "final synthesized answer"
    assert captured["query"] == state["query"]
    assert captured["sql_result"] == state["sql_result"]
    assert captured["policy_result"] == state["policy_result"]


def test_run_invokes_graph(monkeypatch):
    agent = graph_module.SupportMultiAgent()

    class FakeCompiledGraph:
        def invoke(self, state):
            return {**state, "final_answer": "done", "intent": "structured"}

    agent.graph = FakeCompiledGraph()
    result = agent.run("Show Rachel's orders")

    assert result["query"] == "Show Rachel's orders"
    assert result["tools_called"] == []
    assert result["final_answer"] == "done"
