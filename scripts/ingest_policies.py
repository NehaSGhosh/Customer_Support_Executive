import sys
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from app.config import POLICY_DIR, FAISS_DIR
from app.llm import get_embeddings


def load_documents():
    docs = []
    for pdf in Path(POLICY_DIR).glob("*.pdf"):
        loaded = PyPDFLoader(str(pdf)).load()
        for doc in loaded:
            text = doc.page_content.strip()
            if text:
                doc.metadata["source"] = pdf.name
                docs.append(doc)
    return docs

if __name__ == "__main__":
    policy_root = Path(POLICY_DIR)

    if not policy_root.exists():
        print(
            f"Policy directory not found: {policy_root}\n"
            "Please create the folder and add policy PDF files.",
            file=sys.stderr,
        )
        sys.exit(1)

    pdfs = sorted(policy_root.glob("*.pdf"))

    if not pdfs:
        print(
            f"No PDF files found in {policy_root}\n"
            "Please add policy documents (e.g., refund_policy.pdf) before running ingestion.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Found {len(pdfs)} policy documents. Loading...")

    documents = load_documents()

    print(f"Loaded {len(documents)} pages")
    for i, doc in enumerate(documents[:5]):
        print(f"Doc {i} length:", len(doc.page_content.strip()))
        print(repr(doc.page_content[:200]))

    if not documents:
        print(
            "No content extracted from PDFs. Ensure files are readable.",
            file=sys.stderr,
        )
        sys.exit(1)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=80
    )
    
    chunks = splitter.split_documents(documents)

    if not chunks:
        print("Chunking produced no segments.", file=sys.stderr)
        sys.exit(1)

    print(f"Created {len(chunks)} chunks. Generating embeddings...")

    FAISS.from_documents(chunks, get_embeddings()).save_local(str(FAISS_DIR))

    print(f"Indexed {len(chunks)} chunks into {FAISS_DIR}")