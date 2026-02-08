"""
FastAPI application entry point.

- Mounts all routers under /api
- Adds CORS so the Chrome extension can call the backend
- Auto-creates database tables on startup
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend.routers import scrape, surveillance, rank, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup (if they don't exist yet)."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Job Scrape Agent",
    description="AI-powered job scraping, tracking, and ranking",
    version="0.1.0",
    lifespan=lifespan,
)

# Allow the Chrome extension (and any localhost frontend) to call our API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # Chrome extensions use chrome-extension:// origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routers under /api
app.include_router(scrape.router, prefix="/api", tags=["scrape"])
app.include_router(surveillance.router, prefix="/api", tags=["surveillance"])
app.include_router(rank.router, prefix="/api", tags=["rank"])
app.include_router(settings.router, prefix="/api", tags=["settings"])


@app.get("/")
def root():
    """Health check endpoint."""
    return {"status": "ok", "message": "Job Scrape Agent API is running"}
