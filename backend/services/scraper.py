"""
HTML scraper for career pages.

Two modes:
1. parse_html(html) — parse HTML string already grabbed by the Chrome extension
2. fetch_and_parse(url) — fetch the URL server-side and parse (used by surveillance)

The scraper looks for common career page patterns:
- Links inside job listing containers
- Structured data (JSON-LD)
- Common CSS classes (job-title, posting-title, etc.)

No LLM is used here — this is pure HTML parsing with BeautifulSoup.
"""

import json
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup


def parse_html(html: str, base_url: str = "") -> list[dict]:
    """
    Extract job listings from raw HTML.

    Returns a list of dicts: [{"title": "...", "url": "...", "external_id": "...", "posted_at": "..."}]
    Each field except 'title' may be None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # Strategy 1: Look for JSON-LD structured data (many career sites use this)
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            # Handle both single objects and arrays
            items = data if isinstance(data, list) else [data]
            for item in items:
                if item.get("@type") == "JobPosting":
                    jobs.append({
                        "title": item.get("title", ""),
                        "url": item.get("url"),
                        "external_id": item.get("identifier", {}).get("value") if isinstance(item.get("identifier"), dict) else None,
                        "posted_at": item.get("datePosted"),
                    })
        except (json.JSONDecodeError, AttributeError):
            continue

    # Strategy 2: Look for links with job-related patterns in their containers
    # Common patterns: class names containing "job", "posting", "position", "opening"
    job_patterns = re.compile(r"job|posting|position|opening|career|vacancy|role", re.I)

    for link in soup.find_all("a", href=True):
        # Check if the link or its parent has a job-related class
        parent = link.parent
        link_classes = " ".join(link.get("class", []))
        parent_classes = " ".join(parent.get("class", [])) if parent else ""
        all_classes = f"{link_classes} {parent_classes}"

        if job_patterns.search(all_classes) or job_patterns.search(link.get("href", "")):
            title = link.get_text(strip=True)
            if title and len(title) > 3 and len(title) < 200:  # filter out noise
                href = link["href"]
                # Make relative URLs absolute
                if href.startswith("/") and base_url:
                    href = base_url.rstrip("/") + href

                jobs.append({
                    "title": title,
                    "url": href,
                    "external_id": _extract_job_id(href),
                    "posted_at": None,
                })

    # Deduplicate by title+url
    seen = set()
    unique_jobs = []
    for job in jobs:
        key = (job["title"], job.get("url"))
        if key not in seen:
            seen.add(key)
            unique_jobs.append(job)

    return unique_jobs


def fetch_and_parse(url: str) -> list[dict]:
    """
    Fetch a career page URL server-side and extract job listings.
    Used by the surveillance feature (backend fetches directly, no browser needed).
    """
    response = httpx.get(url, follow_redirects=True, timeout=30.0, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    response.raise_for_status()

    # Extract base URL for resolving relative links
    from urllib.parse import urlparse
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    return parse_html(response.text, base_url)


def _extract_job_id(url: str) -> Optional[str]:
    """Try to pull a job ID from the URL (common patterns like /jobs/12345 or ?id=12345)."""
    # Pattern: /jobs/12345 or /positions/12345
    match = re.search(r"/(?:jobs?|positions?|openings?)/(\w+[-]?\w+)", url)
    if match:
        return match.group(1)
    # Pattern: ?id=12345 or ?jobId=12345
    match = re.search(r"[?&](?:id|jobId|job_id)=(\w+)", url)
    if match:
        return match.group(1)
    return None
