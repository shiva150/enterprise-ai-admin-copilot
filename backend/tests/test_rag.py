import pytest

from app.rag.ingest import load_mock_docs
from app.rag.store import build_index, retrieve


@pytest.fixture(scope="module", autouse=True)
def _built_index():
    docs = load_mock_docs()
    assert len(docs) > 0, "No mock docs found — check backend/data/mock/*.json"
    build_index(docs)
    yield


def test_retrieve_returns_k_docs():
    results = retrieve("login failure", k=3)
    assert len(results) == 3


def test_retrieve_is_deterministic():
    r1 = [d.page_content for d in retrieve("user access", k=2)]
    r2 = [d.page_content for d in retrieve("user access", k=2)]
    assert r1 == r2


def test_retrieve_preserves_metadata():
    results = retrieve("admin role", k=1)
    assert "kind" in results[0].metadata


def test_retrieve_by_unique_keyword_auditor():
    # "auditor" is a rare token that appears in exactly one doc
    results = retrieve("auditor", k=1)
    assert results[0].metadata.get("kind") == "rbac"
    assert results[0].metadata.get("role") == "auditor"


def test_retrieve_by_unique_keyword_intern():
    results = retrieve("intern", k=1)
    assert results[0].metadata.get("role") == "intern"


def test_retrieve_etl_query_surfaces_etl_doc():
    results = retrieve("ETL pipeline job failure", k=2)
    services = [r.metadata.get("service") for r in results]
    assert "etl-pipeline" in services
