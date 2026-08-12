#!/usr/bin/env python3
"""
Internship scraper for Jayden's tracker.

Pulls live listings from public Greenhouse and Lever job-board APIs for a
curated list of bioengineering / biotech / medtech / hardware companies,
filters for internship roles, tags them by relevance to Jayden's resume
skills, and writes the result to data/listings.json.

This is designed to run on a schedule via GitHub Actions (see
.github/workflows/update.yml). No API keys required - these are public,
unauthenticated endpoints companies use to power their own careers pages.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "data" / "listings.json"

# ---------------------------------------------------------------------------
# Company sources. Add/remove tokens freely - a wrong or dead token is just
# skipped, it won't break the run.
#
# Greenhouse token = the slug in boards.greenhouse.io/<TOKEN>
# Lever token       = the slug in jobs.lever.co/<TOKEN>
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES = [
    "ginkgobioworks",
    "10xgenomics",
    "benchling",
    "recursionpharmaceuticals",
    "generatebiomedicines",
    "insitro",
    "asimov",
    "arcinstitute",
    "xaira",
    "stryker",
    "bostonscientific",
    "edwards",
    "dexcom",
    "illumina",
    "modernatx",
    "regeneron",
    "vertexpharmaceuticals",
    "biogen",
    "amgen",
    "gilead",
    "vir",
    "intuitivesurgical",
    "abbott",
]

LEVER_COMPANIES = [
    "notablehealth",
    "formlabs",
    "desktopmetal",
    "carbon3d",
    "resmed",
]

# Keywords pulled from Jayden's resume/major - used only to TAG relevance,
# not to filter roles out.
RESUME_KEYWORDS = [
    "bioengineering", "biomedical", "biotech", "biotechnology",
    "medical device", "hardware", "embedded", "firmware", "arduino",
    "cad", "sensor", "wearable", "automation", "lab", "research",
    "computational", "hpc", "protein", "python", "prototyp",
]

INTERN_PATTERN = re.compile(r"\bintern(ship)?\b", re.IGNORECASE)

HEADERS = {"User-Agent": "internship-tracker/1.0 (personal project)"}


def fetch_json(url, retries=2, delay=1.5):
    for attempt in range(retries + 1):
        try:
            req = Request(url, headers=HEADERS)
            with urlopen(req, timeout=20) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as e:
            if attempt == retries:
                print(f"  [skip] {url} -> {e}", file=sys.stderr)
                return None
            time.sleep(delay)


def tag_relevance(title, location):
    text = f"{title} {location}".lower()
    matched = [kw for kw in RESUME_KEYWORDS if kw in text]
    return matched


def scrape_greenhouse(token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []

    results = []
    for job in data["jobs"]:
        title = job.get("title", "")
        if not INTERN_PATTERN.search(title):
            continue
        location = (job.get("location") or {}).get("name", "Unspecified")
        results.append({
            "id": f"greenhouse-{token}-{job.get('id')}",
            "company": token,
            "title": title,
            "location": location,
            "url": job.get("absolute_url", ""),
            "posted_at": job.get("updated_at", ""),
            "source": "greenhouse",
            "tags": tag_relevance(title, location),
        })
    return results


def scrape_lever(token):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    data = fetch_json(url)
    if not data:
        return []

    results = []
    for job in data:
        title = job.get("text", "")
        if not INTERN_PATTERN.search(title):
            continue
        categories = job.get("categories", {}) or {}
        location = categories.get("location", "Unspecified")
        results.append({
            "id": f"lever-{token}-{job.get('id')}",
            "company": token,
            "title": title,
            "location": location,
            "url": job.get("hostedUrl", ""),
            "posted_at": job.get("createdAt", ""),
            "source": "lever",
            "tags": tag_relevance(title, location),
        })
    return results


def normalize_company_name(token):
    # Light cleanup so raw slugs look presentable in the UI.
    return token.replace("-", " ").replace("_", " ").title()


def main():
    all_listings = []

    print("Scraping Greenhouse boards...")
    for token in GREENHOUSE_COMPANIES:
        jobs = scrape_greenhouse(token)
        print(f"  {token}: {len(jobs)} internship postings")
        all_listings.extend(jobs)

    print("Scraping Lever boards...")
    for token in LEVER_COMPANIES:
        jobs = scrape_lever(token)
        print(f"  {token}: {len(jobs)} internship postings")
        all_listings.extend(jobs)

    for listing in all_listings:
        listing["company"] = normalize_company_name(listing["company"])

    # Sort: most relevant (more matched tags) first, then most recently posted.
    all_listings.sort(
        key=lambda x: (-len(x["tags"]), x.get("posted_at", "")),
        reverse=False,
    )
    all_listings.sort(key=lambda x: len(x["tags"]), reverse=True)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(all_listings),
        "listings": all_listings,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"\nWrote {len(all_listings)} listings to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
