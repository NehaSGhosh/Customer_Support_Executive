import app.tools.response_tool as response_tool


class FakeLLM:
    def __init__(self, captured):
        self.captured = captured
    def invoke(self, prompt):
        self.captured["prompt"] = prompt
        return type("Resp", (), {"content": "grounded answer"})()


def test_synthesize_answer_includes_query_sql_and_policy(monkeypatch):
    captured = {}
    monkeypatch.setattr(response_tool, "get_llm", lambda: FakeLLM(captured))

    result = response_tool.synthesize_answer(
        query="Does this qualify for refund?",
        sql_result={"tickets": [{"ticket_id": "t1"}], "orders": [{"order_id": "o1"}]},
        policy_result={"documents": [{"content": "Refunds allowed within 30 days"}]},
    )

    assert result == "grounded answer"
    assert "Does this qualify for refund?" in captured["prompt"]
    assert "ticket_id" in captured["prompt"]
    assert "order_id" in captured["prompt"]
    assert "Refunds allowed within 30 days" in captured["prompt"]
    assert "Use only the provided data" in captured["prompt"]


def test_synthesize_answer_handles_empty_inputs(monkeypatch):
    captured = {}
    monkeypatch.setattr(response_tool, "get_llm", lambda: FakeLLM(captured))

    result = response_tool.synthesize_answer(
        query="What is the refund policy?",
        sql_result={},
        policy_result={},
    )

    assert result == "grounded answer"
    assert "{}" in captured["prompt"]
