"""
Resume-vs-job ranking using the LLM.

Takes the user's resume text and a list of jobs, asks the LLM to score
each job's relevance (1-10), then adds a recency bonus for newer postings.
"""

import json
from datetime import datetime

from backend.services.llm import get_llm


# Prompt sent to the LLM for scoring jobs against a resume
RANK_PROMPT = """You are a job-fit evaluator. Score how well each job matches the candidate's resume.

RESUME:
{resume_text}

JOBS TO EVALUATE:
{jobs_json}

For each job, return a JSON array with objects containing:
- "job_id": the job's ID (integer)
- "score": relevance score from 1 to 10 (10 = perfect fit)
- "reason": one sentence explaining the score

Return ONLY the JSON array, no other text. Example:
[{{"job_id": 1, "score": 8, "reason": "Strong match for backend skills"}}]
"""


def rank_jobs(resume_text: str, jobs: list[dict]) -> list[dict]:
    """
    Score and rank jobs against the resume.

    Args:
        resume_text: plain text of the user's resume
        jobs: list of dicts with keys: id, title, company, url, description, posted_at

    Returns:
        sorted list of dicts with: job_id, title, company, url, score, reason, posted_at, combined_score
    """
    if not jobs:
        return []

    llm = get_llm()

    # Prepare a simplified job list for the LLM (don't send full descriptions if too long)
    jobs_for_llm = []
    for job in jobs:
        jobs_for_llm.append({
            "job_id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "description": (job.get("description") or "")[:500],  # truncate long descriptions
        })

    # Ask the LLM to score each job
    prompt = RANK_PROMPT.format(
        resume_text=resume_text[:3000],  # truncate very long resumes
        jobs_json=json.dumps(jobs_for_llm, indent=2),
    )

    response = llm.invoke(prompt)
    response_text = response.content if hasattr(response, "content") else str(response)

    # Parse the LLM's JSON response
    try:
        # Extract JSON array from response (in case LLM adds extra text)
        json_match = response_text[response_text.index("["):response_text.rindex("]") + 1]
        scores = json.loads(json_match)
    except (ValueError, json.JSONDecodeError):
        # If parsing fails, return jobs with zero scores
        return [
            {**job, "score": 0, "reason": "Failed to parse LLM response", "combined_score": 0}
            for job in jobs
        ]

    # Build a lookup from job_id to LLM score
    score_map = {s["job_id"]: s for s in scores}

    # Combine LLM scores with recency bonus and build final results
    results = []
    for job in jobs:
        llm_result = score_map.get(job["id"], {"score": 0, "reason": "Not scored"})
        relevance = llm_result["score"]
        recency = _recency_bonus(job.get("posted_at"))

        results.append({
            "job_id": job["id"],
            "title": job["title"],
            "company": job["company"],
            "url": job.get("url"),
            "score": relevance,
            "reason": llm_result["reason"],
            "posted_at": job.get("posted_at"),
            "combined_score": round(relevance + recency, 1),
        })

    # Sort by combined score, highest first
    results.sort(key=lambda x: x["combined_score"], reverse=True)
    return results


def _recency_bonus(posted_at) -> float:
    """
    Give a bonus for recently posted jobs.
    - Posted today: +2.0
    - Each day older: -0.1
    - After 20 days: no bonus
    """
    if not posted_at:
        return 0.0

    if isinstance(posted_at, str):
        try:
            posted_at = datetime.fromisoformat(posted_at)
        except ValueError:
            return 0.0

    days_old = (datetime.utcnow() - posted_at).days
    return max(0.0, 2.0 - (days_old * 0.1))
