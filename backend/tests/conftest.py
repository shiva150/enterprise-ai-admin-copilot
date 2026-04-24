"""Test-harness setup.

Runs before any test module is imported:
1. Forces deterministic mock mode (no OpenAI calls in tests).
2. Redirects the FAISS index to a tmp directory.
3. Redirects the SQLite DB to a tmp file.

Both redirections prevent tests from clobbering live dev state.
"""

import os
import shutil
import tempfile
from pathlib import Path

os.environ["USE_MOCK_LLM"] = "1"

_TMP_ROOT = Path(tempfile.gettempdir()) / "enterprise_ai_admin_tests"
_TMP_ROOT.mkdir(parents=True, exist_ok=True)

# Fresh FAISS tmp dir every run
_TEST_INDEX_DIR = _TMP_ROOT / "faiss_index"
if _TEST_INDEX_DIR.exists():
    shutil.rmtree(_TEST_INDEX_DIR, ignore_errors=True)

# Fresh SQLite tmp file every run
_TEST_DB_PATH = _TMP_ROOT / "mock.db"
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

import app.rag.store as _store  # noqa: E402
import app.db.queries as _q  # noqa: E402

_store.INDEX_DIR = _TEST_INDEX_DIR
_q.DB_PATH = _TEST_DB_PATH
