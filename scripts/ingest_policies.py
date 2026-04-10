import json
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import POLICY_DIR, FAISS_DIR, CHUNK_OVERLAP, CHUNK_SIZE
from app.llm import get_embeddings


CHECKPOINT_FILE = Path("data/ingestion_checkpoint.json")
LOCK_FILE = Path("data/ingestion.lock")


def acquire_lock(lock_file: Path, timeout_seconds: int = 10) -> None:
    start = time.time()
    while lock_file.exists():
        if time.time() - start > timeout_seconds:
            raise RuntimeError(f"Another ingestion is already running: {lock_file}")
        time.sleep(0.5)

    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(str(time.time()), encoding="utf-8")


def release_lock(lock_file: Path) -> None:
    if lock_file.exists():
        lock_file.unlink()


def load_checkpoint(checkpoint_file: Path) -> dict[str, float]:
    if not checkpoint_file.exists():
        return {}

    try:
        data = json.loads(checkpoint_file.read_text(encoding="utf-8"))
        return data.get("processed_pdfs", {})
    except Exception:
        return {}


def save_checkpoint(checkpoint_file: Path, processed: dict[str, float]) -> None:
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "processed_pdfs": processed,
        "updated_at": time.time(),
    }
    checkpoint_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_modified_time(pdf_path: Path) -> float:
    return pdf_path.stat().st_mtime


def validate_policy_dir(policy_dir: Path) -> List[Path]:
    if not policy_dir.exists():
        raise FileNotFoundError(
            f"Policy directory not found: {policy_dir}. "
            "Please create it and add PDF files."
        )

    pdf_files = sorted(policy_dir.glob("*.pdf"))
    if not pdf_files:
        raise FileNotFoundError(
            f"No PDF files found in {policy_dir}. "
            "Please add policy documents before running ingestion."
        )

    return pdf_files


def load_single_pdf(pdf_path: Path):
    loaded_docs = PyPDFLoader(str(pdf_path)).load()
    cleaned_docs = []

    for doc in loaded_docs:
        text = doc.page_content.strip()
        if text:
            doc.metadata["source"] = pdf_path.name
            cleaned_docs.append(doc)

    return cleaned_docs


def load_all_documents(pdf_files: List[Path]):
    all_documents = []

    for idx, pdf_path in enumerate(pdf_files, start=1):
        print(f"[{idx}/{len(pdf_files)}] Loading {pdf_path.name}...")
        docs = load_single_pdf(pdf_path)

        if not docs:
            print(f"  No readable content found in {pdf_path.name}. Skipping.")
            continue

        all_documents.extend(docs)
        print(f"  Loaded {len(docs)} non-empty pages from {pdf_path.name}")

    return all_documents


def atomic_replace_dir(src_dir: Path, dst_dir: Path) -> None:
    backup_dir = None

    if dst_dir.exists():
        backup_dir = dst_dir.parent / f"{dst_dir.name}_backup_{int(time.time())}"
        shutil.move(str(dst_dir), str(backup_dir))

    try:
        shutil.move(str(src_dir), str(dst_dir))
        if backup_dir and backup_dir.exists():
            shutil.rmtree(backup_dir)
    except Exception:
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        if backup_dir and backup_dir.exists():
            shutil.move(str(backup_dir), str(dst_dir))
        raise


def ingest_with_checkpoints(
    policy_dir: Path,
    faiss_dir: Path,
    checkpoint_file: Path,
    lock_file: Path,
) -> None:
    acquire_lock(lock_file)

    try:
        pdf_files = validate_policy_dir(policy_dir)
        processed = load_checkpoint(checkpoint_file)

        print(f"Found {len(pdf_files)} PDF files.")
        print(f"Checkpoint has {len(processed)} tracked PDFs.")

        changes_detected = False
        new_checkpoint: dict[str, float] = {}

        for idx, pdf_path in enumerate(pdf_files, start=1):
            current_mtime = get_modified_time(pdf_path)
            saved_mtime = processed.get(pdf_path.name)

            new_checkpoint[pdf_path.name] = current_mtime

            if saved_mtime is None:
                print(f"[{idx}/{len(pdf_files)}] New file detected: {pdf_path.name}")
                changes_detected = True
            elif current_mtime != saved_mtime:
                print(f"[{idx}/{len(pdf_files)}] Modified file detected: {pdf_path.name}")
                changes_detected = True
            else:
                print(f"[{idx}/{len(pdf_files)}] Unchanged file: {pdf_path.name}")

        # Also detect deleted files
        old_files = set(processed.keys())
        current_files = {pdf.name for pdf in pdf_files}
        deleted_files = old_files - current_files

        if deleted_files:
            print(f"Deleted files detected: {sorted(deleted_files)}")
            changes_detected = True

        if not changes_detected:
            print("No new, modified, or deleted PDFs detected. Skipping ingestion.")
            return

        print("Changes detected. Rebuilding FAISS index from all current PDFs...")

        all_documents = load_all_documents(pdf_files)

        if not all_documents:
            raise RuntimeError("No readable content extracted from current PDFs.")

        print(f"Splitting {len(all_documents)} loaded pages into chunks...")
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
        chunks = splitter.split_documents(all_documents)

        if not chunks:
            raise RuntimeError("Chunking produced no segments.")

        print(f"Created {len(chunks)} chunks. Building FAISS index...")

        with tempfile.TemporaryDirectory(prefix="faiss_build_") as tmp_dir:
            tmp_index_dir = Path(tmp_dir) / "faiss_index"

            vectorstore = FAISS.from_documents(chunks, get_embeddings())
            vectorstore.save_local(str(tmp_index_dir))

            print(f"Temporary index built at: {tmp_index_dir}")
            print(f"Publishing index to: {faiss_dir}")

            faiss_dir.parent.mkdir(parents=True, exist_ok=True)
            atomic_replace_dir(tmp_index_dir, faiss_dir)

        save_checkpoint(checkpoint_file, new_checkpoint)
        print("Ingestion completed successfully.")

    finally:
        release_lock(lock_file)


if __name__ == "__main__":
    try:
        ingest_with_checkpoints(
            policy_dir=Path(POLICY_DIR),
            faiss_dir=Path(FAISS_DIR),
            checkpoint_file=CHECKPOINT_FILE,
            lock_file=LOCK_FILE,
        )
    except Exception as e:
        print(f"Ingestion failed: {e}", file=sys.stderr)
        sys.exit(1)