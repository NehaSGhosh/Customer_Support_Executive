from pathlib import Path
from types import SimpleNamespace
import scripts.ingest_policies as ingest


def test_load_all_documents_reads_pdfs_and_skips_blank_pages(monkeypatch, tmp_path):
    policy_dir = tmp_path / "policies"
    policy_dir.mkdir()
    pdf1 = policy_dir / "refund.pdf"
    pdf2 = policy_dir / "privacy.pdf"
    pdf1.write_text("dummy")
    pdf2.write_text("dummy")

    docs_by_path = {
        str(pdf1): [
            SimpleNamespace(page_content=" Refund policy text ", metadata={}),
            SimpleNamespace(page_content="   ", metadata={}),
        ],
        str(pdf2): [
            SimpleNamespace(page_content="Privacy text", metadata={}),
        ],
    }

    class FakeLoader:
        def __init__(self, path):
            self.path = path
        def load(self):
            return docs_by_path[self.path]

    monkeypatch.setattr(ingest, "PyPDFLoader", FakeLoader)

    docs = ingest.load_all_documents([pdf1, pdf2])

    assert len(docs) == 2
    assert docs[0].metadata["source"] == "refund.pdf"
    assert docs[1].metadata["source"] == "privacy.pdf"
    assert docs[0].page_content.strip() == "Refund policy text"
    assert docs[1].page_content == "Privacy text"


def test_load_documents_returns_empty_when_no_pdfs(monkeypatch, tmp_path):
    policy_dir = tmp_path / "empty_policies"
    policy_dir.mkdir()

    try:
        ingest.validate_policy_dir(policy_dir)
        assert False, "Expected FileNotFoundError when no PDFs exist"
    except FileNotFoundError as exc:
        assert "No PDF files found" in str(exc)
