import hashlib
import re

import numpy as np
from langchain_core.embeddings import Embeddings

from app.config import settings

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


class DeterministicMockEmbeddings(Embeddings):
    """Hashing-trick bag-of-words embeddings — same text always maps to the same
    vector, shared tokens produce correlated vectors. Used only when
    `USE_MOCK_LLM=1` for offline tests/demos. Real retrieval quality comes
    from the Gemini embedding model."""

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def _token_vec(self, token: str) -> np.ndarray:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "big", signed=False) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.standard_normal(self.dim).astype(np.float32)

    def _embed(self, text: str) -> list[float]:
        vec = np.zeros(self.dim, dtype=np.float32)
        for token in _TOKEN_RE.findall(text.lower()):
            vec += self._token_vec(token)
        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def get_embeddings() -> Embeddings:
    if settings.use_mock_llm:
        return DeterministicMockEmbeddings()

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is empty. Set it in backend/.env "
            "(get one at https://aistudio.google.com/apikey) or flip USE_MOCK_LLM=1."
        )

    from langchain_google_genai import GoogleGenerativeAIEmbeddings

    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
    )
