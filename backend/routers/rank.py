"""
Rank router — Feature 3: Rate & Rank.

Endpoints:
- POST /api/resume  — upload a resume (PDF or text file)
- GET  /api/rank    — rank all stored jobs against the resume
"""

import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Job, Resume
from backend.schemas import RankedJob, ResumeOut
from backend.services.ranker import rank_jobs

router = APIRouter()


@router.post("/resume", response_model=ResumeOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a resume file (PDF or plain text).
    Extracts text and stores it. Overwrites any previously uploaded resume.
    """
    content_bytes = await file.read()

    # Extract text based on file type
    if file.filename and file.filename.lower().endswith(".pdf"):
        text = _extract_pdf_text(content_bytes)
    else:
        # Assume plain text
        text = content_bytes.decode("utf-8", errors="ignore")

    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from the uploaded file.")

    # Overwrite existing resume (we only keep one)
    existing = db.query(Resume).first()
    if existing:
        existing.filename = file.filename
        existing.content = text
    else:
        existing = Resume(filename=file.filename, content=text)
        db.add(existing)

    db.commit()
    db.refresh(existing)
    return existing


@router.get("/rank", response_model=list[RankedJob])
def rank_stored_jobs(limit: int = 20, db: Session = Depends(get_db)):
    """
    Rank all stored jobs against the user's resume.
    Returns jobs sorted by combined score (relevance + recency).
    """
    # Get the resume
    resume = db.query(Resume).first()
    if not resume:
        raise HTTPException(status_code=400, detail="No resume uploaded yet. Upload one first via POST /api/resume.")

    # Get all jobs (with company info)
    jobs = db.query(Job).all()
    if not jobs:
        raise HTTPException(status_code=400, detail="No jobs in database. Run surveillance or scrape first.")

    # Build job dicts for the ranker
    job_dicts = []
    for job in jobs:
        job_dicts.append({
            "id": job.id,
            "title": job.title,
            "company": job.company.name,
            "url": job.url,
            "description": job.description,
            "posted_at": job.posted_at,
        })

    # Run the ranking
    ranked = rank_jobs(resume.content, job_dicts)

    # Return top N results
    return [RankedJob(**r) for r in ranked[:limit]]


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract plain text from PDF bytes using PyPDF2."""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception:
        return ""
