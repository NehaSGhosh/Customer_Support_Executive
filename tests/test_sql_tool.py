from types import SimpleNamespace
import app.tools.sql_tool as sql_tool


class Extraction(SimpleNamespace):
    pass


def test_safe_llm_call_returns_on_first_success():
    assert sql_tool.safe_llm_call(lambda: "ok") == "ok"


def test_safe_llm_call_raises_for_non_rate_limit():
    def fake_fn():
        raise ValueError("some other failure")

    try:
        sql_tool.safe_llm_call(fake_fn)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "some other failure" in str(exc)


def test_safe_llm_call_raises_after_retries():
    def fake_fn():
        raise Exception("rate_limit exceeded")

    try:
        sql_tool.safe_llm_call(fake_fn)
        assert False, "Expected terminal exception"
    except Exception as exc:
        assert str(exc) == "LLM failed after retries"


def test_extract_customer_query_info(monkeypatch):
    expected = Extraction(
        customer_name="Ravi Sharma",
        include_profile=False,
        include_tickets=False,
        include_orders=True,
    )

    class FakeStructuredLLM:
        def invoke(self, prompt):
            assert "Ravi Sharma" in prompt
            return expected

    class FakeLLM:
        def with_structured_output(self, schema):
            assert schema is sql_tool.CustomerQueryExtraction
            return FakeStructuredLLM()

    monkeypatch.setattr(sql_tool, "get_llm", lambda: FakeLLM())
    monkeypatch.setattr(sql_tool, "safe_llm_call", lambda fn: fn())

    result = sql_tool.extract_customer_query_info("Show Ravi Sharma's order history")

    assert result.customer_name == "Ravi Sharma"
    assert result.include_orders is True
    assert result.include_profile is False
    assert result.include_tickets is False


def test_lookup_customer_support_data_profile_only(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=True, include_tickets=False, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)

    calls = []
    def fake_run_query(sql, params=None):
        calls.append((sql, params))
        return [{"customer_id": "1", "first_name": "Rachel", "last_name": "Moore"}]

    monkeypatch.setattr(sql_tool, "run_query", fake_run_query)
    result = sql_tool.lookup_customer_support_data("Show Rachel Moore's profile")

    assert result == {
        "error": None,
        "customer": {"customer_id": "1", "first_name": "Rachel", "last_name": "Moore"},
    }
    assert len(calls) == 1
    assert calls[0][1] == ("Rachel Moore",)


def test_lookup_customer_support_data_tickets_only(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=False, include_tickets=True, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: [{"ticket_id": "t1"}, {"ticket_id": "t2"}])

    result = sql_tool.lookup_customer_support_data("Show Rachel Moore's tickets")

    assert result == {"error": None, "tickets": [{"ticket_id": "t1"}, {"ticket_id": "t2"}]}


def test_lookup_customer_support_data_orders_only(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=False, include_tickets=False, include_orders=True)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: [{"order_id": "o1"}])

    result = sql_tool.lookup_customer_support_data("Show Rachel Moore's orders")

    assert result == {
        "error": "Unexpected error while retrieving customer support data.",
        "summary": {},
    }


def test_lookup_customer_support_data_profile_tickets_orders(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=True, include_tickets=True, include_orders=True)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)

    returned = iter([
        [{"customer_id": "1", "first_name": "Rachel"}],
        [{"ticket_id": "t1"}],
        [{"order_id": "o1"}],
    ])
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: next(returned))

    result = sql_tool.lookup_customer_support_data("Give full details for Rachel Moore")

    assert result == {
        "error": "Unexpected error while retrieving customer support data.",
        "summary": {},
    }


def test_lookup_customer_support_data_single_name_uses_none_for_last(monkeypatch):
    extracted = Extraction(customer_name="Ema", include_profile=True, include_tickets=False, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)

    captured = {}
    def fake_run_query(sql, params=None):
        captured["params"] = params
        return [{"customer_id": "1", "first_name": "Ema"}]

    monkeypatch.setattr(sql_tool, "run_query", fake_run_query)
    result = sql_tool.lookup_customer_support_data("Show Ema's profile")

    assert result["customer"]["first_name"] == "Ema"
    assert captured["params"] == ("Ema",)


def test_lookup_customer_support_data_profile_empty_result(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=True, include_tickets=False, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: [])

    result = sql_tool.lookup_customer_support_data("Show Rachel Moore's profile")

    assert result == {"error": None, "customer": {}}


def test_lookup_customer_support_data_tickets_empty_result(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=False, include_tickets=True, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: [])

    result = sql_tool.lookup_customer_support_data("Show Rachel Moore's tickets")

    assert result == {"error": None, "tickets": []}


def test_lookup_customer_support_data_orders_empty_result(monkeypatch):
    extracted = Extraction(customer_name="Rachel Moore", include_profile=False, include_tickets=False, include_orders=True)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: [])

    result = sql_tool.lookup_customer_support_data("Show Rachel Moore's orders")

    assert result == {
        "error": "Unexpected error while retrieving customer support data.",
        "summary": {},
    }


def test_lookup_customer_support_data_no_customer_name_returns_fallback(monkeypatch):
    extracted = Extraction(customer_name=None, include_profile=False, include_tickets=False, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)

    calls = []
    def fake_run_query(sql, params=None):
        calls.append((sql, params))
        return [{"open_tickets": 12}]

    monkeypatch.setattr(sql_tool, "run_query", fake_run_query)
    result = sql_tool.lookup_customer_support_data("How many open tickets are there?")

    assert result == {"summary": {"open_tickets": 12}, "error": None}
    assert len(calls) == 1
    assert calls[0][1] is None


def test_lookup_customer_support_data_no_customer_name_empty_fallback(monkeypatch):
    extracted = Extraction(customer_name=None, include_profile=False, include_tickets=False, include_orders=False)
    monkeypatch.setattr(sql_tool, "extract_customer_query_info", lambda q: extracted)
    monkeypatch.setattr(sql_tool, "run_query", lambda sql, params=None: [])

    result = sql_tool.lookup_customer_support_data("How many open tickets are there?")

    assert result == {"summary": {}, "error": None}
