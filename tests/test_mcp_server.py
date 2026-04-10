import app.mcp_server as mcp_server


def test_sql_lookup_delegates_to_lookup_customer_support_data(monkeypatch):
    monkeypatch.setattr(mcp_server, "lookup_customer_support_data", lambda query: {"query": query, "kind": "sql"})

    result = mcp_server.sql_lookup("Show Rachel's profile")

    assert result == {"query": "Show Rachel's profile", "kind": "sql"}


def test_policy_search_delegates_to_search_policy_knowledge(monkeypatch):
    monkeypatch.setattr(mcp_server, "search_policy_knowledge", lambda query: {"query": query, "kind": "policy"})

    result = mcp_server.policy_search("refund policy")

    assert result == {"query": "refund policy", "kind": "policy"}
