"""
Pydantic schemas for request/response validation.

These define the shape of data going in and out of our API endpoints.
FastAPI uses these to auto-validate requests and generate API docs.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


# ─── Scrape (Feature 1) ─────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    """What the Chrome extension sends when user clicks 'Search'."""
    url: str                    # the career page URL (for reference)
    titles: list[str]           # desired job titles, e.g. ["software engineer", "ML engineer"]
    page_html: str              # full HTML of the career page (grabbed by content script)


class JobMatch(BaseModel):
    """A single job that matched the user's desired titles."""
    title: str
    url: Optional[str] = None
    relevance: str              # "exact" or "adjacent"


class ScrapeResponse(BaseModel):
    matches: list[JobMatch]


# ─── Surveillance (Feature 2) ───────────────────────────────────────

class CompanyCreate(BaseModel):
    """Add a new company to track."""
    name: str
    career_url: str


class CompanyOut(BaseModel):
    """Company info returned from the API."""
    id: int
    name: str
    career_url: str
    last_checked_at: Optional[datetime] = None

    class Config:
        from_attributes = True      # allows creating from SQLAlchemy model


class NewJob(BaseModel):
    """A newly discovered job from surveillance check."""
    company: str
    title: str
    url: Optional[str] = None
    posted_at: Optional[datetime] = None


class SurveillanceResponse(BaseModel):
    new_jobs: list[NewJob]


# ─── Rank (Feature 3) ───────────────────────────────────────────────

class ResumeOut(BaseModel):
    id: int
    filename: Optional[str] = None

    class Config:
        from_attributes = True


class RankedJob(BaseModel):
    """A job scored against the user's resume."""
    job_id: int
    title: str
    company: str
    url: Optional[str] = None
    score: float                # LLM relevance score (1-10)
    reason: str                 # one-sentence explanation
    posted_at: Optional[datetime] = None
    combined_score: float       # relevance + recency bonus


# ─── Settings ────────────────────────────────────────────────────────

class SettingsOut(BaseModel):
    llm_provider: str
    ollama_model: Optional[str] = None


class SettingsUpdate(BaseModel):
    llm_provider: str           # "ollama", "gemini", "claude", "openai"
    api_key: Optional[str] = None
    ollama_model: Optional[str] = None
