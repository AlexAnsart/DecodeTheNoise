"""Configuration read once from the environment (and `.env` in development)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

from backend.model_client.embedding import EmbeddingKey


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # The build the server loads at start-up (see backend/map/schema.py).
    data_build_dir: Path = Path("data/build/current")

    # Embedding role. Local mode: an Ollama endpoint we run. Hosted mode: the AI Router.
    embedding_api_base: str = "http://localhost:11434/v1"
    embedding_api_key: str = "ollama"
    embedding_model: str = "embeddinggemma"
    embedding_revision: str = "latest"
    embedding_prefix: str = "task: classification | query: "
    embedding_dims: int = 256

    # LLM role: the Hostinger AI Router.
    llm_api_base: str = "https://router.hostinger.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""

    git_commit: str = "dev"

    def embedding_key(self) -> EmbeddingKey:
        return EmbeddingKey(
            model=self.embedding_model,
            revision=self.embedding_revision,
            prefix=self.embedding_prefix,
            dims=self.embedding_dims,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
