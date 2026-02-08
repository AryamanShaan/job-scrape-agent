"""
Settings router — configure the LLM provider at runtime.

Endpoints:
- GET /api/settings  — get current LLM config
- PUT /api/settings  — update LLM provider and API key
"""

import os

from fastapi import APIRouter

from backend.config import settings
from backend.schemas import SettingsOut, SettingsUpdate

router = APIRouter()


@router.get("/settings", response_model=SettingsOut)
def get_settings():
    """Return current LLM configuration (no secrets exposed)."""
    return SettingsOut(
        llm_provider=settings.LLM_PROVIDER,
        ollama_model=settings.OLLAMA_MODEL if settings.LLM_PROVIDER == "ollama" else None,
    )


@router.put("/settings")
def update_settings(data: SettingsUpdate):
    """
    Update LLM provider at runtime.
    Changes are held in memory (lost on restart). For persistence, edit .env.
    """
    settings.LLM_PROVIDER = data.llm_provider

    if data.api_key:
        settings.LLM_API_KEY = data.api_key

    if data.ollama_model:
        settings.OLLAMA_MODEL = data.ollama_model

    return {"status": "ok", "llm_provider": settings.LLM_PROVIDER}
