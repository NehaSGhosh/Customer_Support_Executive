import app.tools.policy_tool as policy_tool


def test_search_policy_knowledge_wraps_documents(monkeypatch):
    monkeypatch.setattr(
        policy_tool,
        "search_policies",
        lambda query: [{"content": "refund rule", "metadata": {"source": "refund.pdf"}}],
    )

    result = policy_tool.search_policy_knowledge("refund policy")

    assert result == {
        "documents": [{"content": "refund rule", "metadata": {"source": "refund.pdf"}}],
        "error": None,
    }
