"""
Scrape router — Feature 1: Search/Scrape.

Endpoint: POST /api/scrape
- Receives career page HTML + desired job titles from the Chrome extension
- Parses the HTML for job listings (BeautifulSoup)
- Uses the LLM to fuzzy-match titles (e.g. "software engineer" ≈ "software developer")
- Returns matching jobs
"""

import json

from fastapi import APIRouter

from backend.schemas import ScrapeRequest, ScrapeResponse, JobMatch
from backend.services.scraper import parse_html
from backend.services.llm import get_llm

router = APIRouter()

# Prompt for the LLM to fuzzy-match job titles
TITLE_MATCH_PROMPT = """Given these desired job titles: {desired_titles}

And these job listings found on a career page:
{job_list}

Return a JSON array of jobs that match or are closely adjacent to the desired titles.
A job matches if its title is the same role or a closely related role. Examples:
- "Software Engineer" matches "Software Developer", "Backend Engineer", "SWE II"
- "Machine Learning Engineer" matches "ML Research Engineer", "AI Engineer"
Be inclusive for genuine matches, but don't match unrelated roles.

Return format (JSON array only, no other text):
[{{"title": "exact title from listing", "url": "url if available", "relevance": "exact or adjacent"}}]

If no jobs match, return an empty array: []
"""


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_career_page(request: ScrapeRequest):
    """
    Scrape a career page for jobs matching the user's desired titles.
    The Chrome extension grabs the page HTML and sends it here.
    """
    # Step 1: Parse the raw HTML to extract all job listings
    raw_jobs = parse_html(request.page_html, request.url)

    if not raw_jobs:
        return ScrapeResponse(matches=[])

    # Step 2: Ask the LLM which jobs match the user's desired titles
    job_list_str = "\n".join(
        f"- {job['title']} ({job.get('url', 'no url')})" for job in raw_jobs
    )

    prompt = TITLE_MATCH_PROMPT.format(
        desired_titles=", ".join(request.titles),
        job_list=job_list_str,
    )

    llm = get_llm()
    response = llm.invoke(prompt)
    response_text = response.content if hasattr(response, "content") else str(response)

    # Step 3: Parse the LLM's response into structured matches
    try:
        json_str = response_text[response_text.index("["):response_text.rindex("]") + 1]
        matches_raw = json.loads(json_str)
        matches = [JobMatch(**m) for m in matches_raw]
    except (ValueError, json.JSONDecodeError):
        # If LLM response is unparseable, fall back to returning all jobs
        matches = [JobMatch(title=j["title"], url=j.get("url"), relevance="unknown") for j in raw_jobs]

    return ScrapeResponse(matches=matches)
