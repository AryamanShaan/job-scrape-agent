"""
Application settings loaded from .env file.

Uses pydantic-settings to validate and type-check all environment variables.
Copy .env.example to .env and fill in your values before running.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Postgres connection string
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/job_scrape"

    # Which LLM to use: "ollama", "gemini", "claude", or "openai"
    LLM_PROVIDER: str = "ollama"

    # Ollama-specific settings
    OLLAMA_MODEL: str = "llama3"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # API key for cloud LLM providers (not needed for Ollama)
    LLM_API_KEY: str = ""

    class Config:
        env_file = ".env"


# Single global instance — import this wherever you need settings
settings = Settings()
