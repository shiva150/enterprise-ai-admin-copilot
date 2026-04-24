from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from app.config import settings
from app.rag.embeddings import get_embeddings

# Mode-aware index path so mock (384-dim) and Gemini (768-dim) indices can
# coexist on disk. Switching USE_MOCK_LLM no longer requires a re-ingest.
INDEX_DIR: Path = (
    Path(__file__).resolve().parent.parent.parent
    / "data"
    / f"faiss_index_{'mock' if settings.use_mock_llm else 'gemini'}"
)


def build_index(docs: list[Document]) -> FAISS:
    if not docs:
        raise ValueError("Cannot build FAISS index with zero documents.")
    embeddings = get_embeddings()
    store = FAISS.from_documents(docs, embeddings)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    store.save_local(str(INDEX_DIR))
    return store


def load_index() -> FAISS:
    if not INDEX_DIR.exists():
        mode = "mock" if settings.use_mock_llm else "gemini"
        raise FileNotFoundError(
            f"FAISS index not found at {INDEX_DIR}. "
            f"Run `python -m app.rag.ingest` with USE_MOCK_LLM={'1' if mode == 'mock' else '0'} first."
        )
    embeddings = get_embeddings()
    return FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )


def retrieve(query: str, k: int = 3) -> list[Document]:
    store = load_index()
    return store.similarity_search(query, k=k)
