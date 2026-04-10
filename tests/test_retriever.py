from types import SimpleNamespace
import app.retriever as retriever


def test_search_policies_loads_faiss_and_formats_documents(monkeypatch, tmp_path):
    docs = [
        SimpleNamespace(page_content="Refunds accepted within 30 days", metadata={"source": "refund.pdf"}),
        SimpleNamespace(page_content="Privacy notice", metadata={"source": "privacy.pdf"}),
    ]
    captured = {}

    class FakeStore:
        def similarity_search(self, query, k=4):
            captured["query"] = query
            captured["k"] = k
            return docs

    def fake_load_local(path, embeddings, allow_dangerous_deserialization=False):
        captured["path"] = path
        captured["allow"] = allow_dangerous_deserialization
        captured["embeddings"] = embeddings
        return FakeStore()

    monkeypatch.setattr(retriever.FAISS, "load_local", fake_load_local)
    monkeypatch.setattr(retriever, "get_embeddings", lambda: "EMBEDDINGS")
    monkeypatch.setattr(retriever, "FAISS_DIR", str(tmp_path))
    retriever._VECTOR_STORE = None
    tmp_path.mkdir(exist_ok=True)

    result = retriever.search_policies("refund policy")

    assert result == [
        {"content": "Refunds accepted within 30 days", "metadata": {"source": "refund.pdf"}},
        {"content": "Privacy notice", "metadata": {"source": "privacy.pdf"}},
    ]
    assert captured["query"] == "refund policy"
    assert captured["k"] == retriever.TOP_K
    assert captured["allow"] is True
    assert captured["embeddings"] == "EMBEDDINGS"


def test_search_policies_returns_empty_list_when_no_docs(monkeypatch, tmp_path):
    class FakeStore:
        def similarity_search(self, query, k=4):
            return []

    monkeypatch.setattr(retriever.FAISS, "load_local", lambda *args, **kwargs: FakeStore())
    monkeypatch.setattr(retriever, "get_embeddings", lambda: "EMBEDDINGS")
    monkeypatch.setattr(retriever, "FAISS_DIR", str(tmp_path))
    retriever._VECTOR_STORE = None
    tmp_path.mkdir(exist_ok=True)

    assert retriever.search_policies("refund policy") == []


def test_search_policies_propagates_faiss_load_error(monkeypatch, tmp_path):
    def fake_load_local(*_args, **_kwargs):
        raise RuntimeError("index missing")

    monkeypatch.setattr(retriever.FAISS, "load_local", fake_load_local)
    monkeypatch.setattr(retriever, "get_embeddings", lambda: "EMBEDDINGS")
    monkeypatch.setattr(retriever, "FAISS_DIR", str(tmp_path))
    retriever._VECTOR_STORE = None
    tmp_path.mkdir(exist_ok=True)

    try:
        retriever.search_policies("refund policy")
        assert False, "Expected PolicySearchError"
    except retriever.PolicySearchError as exc:
        assert "Unable to load the policy search index" in str(exc)
