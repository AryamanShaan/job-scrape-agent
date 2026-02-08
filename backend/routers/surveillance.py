"""
Surveillance router — Feature 2: Track & Monitor.

Endpoints:
- GET    /api/companies           — list all tracked companies
- POST   /api/companies           — add a company to track
- DELETE /api/companies/{id}      — remove a tracked company
- POST   /api/surveillance/check  — scrape all tracked URLs, find new jobs
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Company, Job
from backend.schemas import CompanyCreate, CompanyOut, NewJob, SurveillanceResponse
from backend.services.scraper import fetch_and_parse

router = APIRouter()


# ─── Company CRUD ────────────────────────────────────────────────────

@router.get("/companies", response_model=list[CompanyOut])
def list_companies(db: Session = Depends(get_db)):
    """Return all tracked companies."""
    return db.query(Company).order_by(Company.name).all()


@router.post("/companies", response_model=CompanyOut)
def add_company(data: CompanyCreate, db: Session = Depends(get_db)):
    """Add a new company career URL to track."""
    # Check for duplicate URL
    existing = db.query(Company).filter(Company.career_url == data.career_url).first()
    if existing:
        raise HTTPException(status_code=400, detail="This URL is already being tracked.")

    company = Company(name=data.name, career_url=data.career_url)
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.delete("/companies/{company_id}", status_code=204)
def remove_company(company_id: int, db: Session = Depends(get_db)):
    """Stop tracking a company (also deletes its stored jobs)."""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    db.delete(company)
    db.commit()


# ─── Surveillance Check ─────────────────────────────────────────────

@router.post("/surveillance/check", response_model=SurveillanceResponse)
def check_for_new_jobs(db: Session = Depends(get_db)):
    """
    Scrape all tracked company URLs and detect new job postings.

    For each company:
    1. Fetch and parse their career page
    2. Compare against jobs already in our database
    3. Insert any new jobs
    4. Return only the newly found jobs
    """
    companies = db.query(Company).all()
    all_new_jobs = []

    for company in companies:
        try:
            # Scrape the career page
            scraped_jobs = fetch_and_parse(company.career_url)
        except Exception as e:
            # If a single company fails, skip it and continue with others
            print(f"Failed to scrape {company.name}: {e}")
            continue

        # Get existing jobs for this company (for dedup)
        existing_jobs = db.query(Job).filter(Job.company_id == company.id).all()
        existing_keys = set()
        for job in existing_jobs:
            if job.external_id:
                existing_keys.add(("eid", job.external_id))
            else:
                existing_keys.add(("tu", job.title, job.url))

        # Find and insert new jobs
        for scraped in scraped_jobs:
            # Check if this job already exists
            if scraped.get("external_id"):
                key = ("eid", scraped["external_id"])
            else:
                key = ("tu", scraped["title"], scraped.get("url"))

            if key in existing_keys:
                continue  # already known, skip

            # New job found — insert it
            new_job = Job(
                company_id=company.id,
                external_id=scraped.get("external_id"),
                title=scraped["title"],
                url=scraped.get("url"),
                posted_at=_parse_date(scraped.get("posted_at")),
                is_new=True,
            )
            db.add(new_job)

            all_new_jobs.append(NewJob(
                company=company.name,
                title=scraped["title"],
                url=scraped.get("url"),
                posted_at=_parse_date(scraped.get("posted_at")),
            ))

        # Update last_checked timestamp
        company.last_checked_at = datetime.utcnow()

    db.commit()

    return SurveillanceResponse(new_jobs=all_new_jobs)


def _parse_date(date_str) -> datetime | None:
    """Try to parse a date string into a datetime. Returns None on failure."""
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None
