"""
SQLAlchemy ORM models — these map directly to Postgres tables.

Three tables:
- companies: career page URLs the user wants to track
- jobs: every job posting we've ever scraped
- resumes: the user's uploaded resume (single row, overwritten on re-upload)
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
)
from sqlalchemy.orm import relationship

from backend.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)                  # e.g. "Stripe"
    career_url = Column(Text, nullable=False, unique=True)      # pre-filtered career page URL
    created_at = Column(DateTime, default=datetime.utcnow)
    last_checked_at = Column(DateTime, nullable=True)           # when surveillance last ran

    # One company has many jobs
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    external_id = Column(String(255), nullable=True)            # job ID from career site (if available)
    title = Column(String(500), nullable=False)
    url = Column(Text, nullable=True)                           # direct link to the posting
    posted_at = Column(DateTime, nullable=True)                 # when the job was posted
    first_seen_at = Column(DateTime, default=datetime.utcnow)   # when we first scraped it
    is_new = Column(Boolean, default=True)                      # flipped to False after user sees it
    description = Column(Text, nullable=True)                   # full job description

    company = relationship("Company", back_populates="jobs")

    # Avoid duplicate jobs: same external_id per company, or same title+url if no external_id
    __table_args__ = (
        UniqueConstraint("company_id", "external_id", name="uq_company_external_id"),
    )


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)          # plain text extracted from PDF/docx
    uploaded_at = Column(DateTime, default=datetime.utcnow)
