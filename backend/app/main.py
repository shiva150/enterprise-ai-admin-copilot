from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes import action, ingest, query

app = FastAPI(title="Enterprise AI Admin Copilot", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router)
app.include_router(action.router)
app.include_router(ingest.router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mock_llm": settings.use_mock_llm,
        "model": settings.gemini_model if not settings.use_mock_llm else "mock",
    }
