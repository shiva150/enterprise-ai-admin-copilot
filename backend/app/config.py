from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Default is real Gemini. Flip to True for offline mock (tests + demos without a key).
    use_mock_llm: bool = False

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "models/gemini-embedding-001"

    frontend_origin: str = "http://localhost:5173"


settings = Settings()
