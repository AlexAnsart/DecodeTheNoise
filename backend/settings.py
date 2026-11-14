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

    # Web reader: Context.dev turns a pasted link into clean text. Without a key the paste box
    # still takes text.
    context_dev_api_base: str = "https://api.context.dev/v1"
    context_dev_api_key: str = ""

    # Workspaces: one folder per workspace, the account registry and the embedding cache.
    # Written by the server, so it lives on a volume, never in the image.
    workspaces_dir: Path = Path("data/workspaces")
    # The probe pack the server reads (`probes.json`, `probes.npz`), and the evaluation reports
    # behind it. Both are committed: they hold weights and measures, no text.
    probes_dir: Path = Path("probes")
    reports_dir: Path = Path("reports")

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
