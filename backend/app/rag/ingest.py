"""Build the FAISS index from mock RBAC + system docs.

Run: `python -m app.rag.ingest`
"""

import json
from pathlib import Path

from langchain_core.documents import Document

from app.rag.store import build_index

MOCK_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "mock"


def load_mock_docs() -> list[Document]:
    docs: list[Document] = []

    rbac_path = MOCK_DIR / "rbac_policies.json"
    if rbac_path.exists():
        for item in json.loads(rbac_path.read_text(encoding="utf-8")):
            content = (
                f"Role: {item['role']}\n"
                f"Permissions: {', '.join(item['permissions'])}\n"
                f"Description: {item['description']}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={"kind": "rbac", "role": item["role"]},
                )
            )

    sys_path = MOCK_DIR / "system_docs.json"
    if sys_path.exists():
        for item in json.loads(sys_path.read_text(encoding="utf-8")):
            content = (
                f"Service: {item['service']}\n"
                f"Topic: {item['topic']}\n"
                f"{item['content']}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "kind": "system",
                        "service": item["service"],
                        "topic": item["topic"],
                    },
                )
            )

    return docs


def main() -> None:
    docs = load_mock_docs()
    print(f"Loaded {len(docs)} mock documents")
    build_index(docs)
    print("FAISS index built and saved.")


if __name__ == "__main__":
    main()
