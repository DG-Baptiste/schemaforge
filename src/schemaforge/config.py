"""Environment-based application configuration."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Runtime settings loaded from environment variables."""

    model_config = ConfigDict(frozen=True)

    base_url: str = Field(default="http://localhost:11434/v1")
    api_key: str = Field(default="ollama", repr=False)
    model: str = Field(default="qwen2.5:1.5b")
    timeout_seconds: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=10)
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls) -> Settings:
        """Build settings without hiding environment access in global state."""
        return cls(
            base_url=os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1").rstrip("/"),
            api_key=os.getenv("OPENAI_API_KEY", "ollama"),
            model=os.getenv("OPENAI_MODEL", "qwen2.5:1.5b"),
            timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
            max_retries=int(os.getenv("LLM_MAX_RETRIES", "2")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
