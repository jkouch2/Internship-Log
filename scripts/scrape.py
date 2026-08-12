#!/usr/bin/env python3
"""
Internship scraper for Jayden's tracker.

Pulls live listings from public Greenhouse, Lever, and Workday job-board
APIs for a curated list of bioengineering / biotech / medtech companies,
filters for internship roles, tags them by relevance to Jayden's resume
skills, and writes the result to data/listings.json.

This is designed to run on a schedule via GitHub Actions (see
.github/workflows/update.yml). No API keys required - these are the same
public, unauthenticated endpoints each company's own careers page calls
in the browser.
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
# Company sources. Every token below has been manually verified against the
# company's live job board. Add/remove freely - a wrong or dead token is
# just skipped, it won't break the run. See README.md for how to verify a
# new one before adding it.
# ---------------------------------------------------------------------------
GREENHOUSE_COMPANIES = [
    "ginkgobioworks",
    "10xgenomics",
    "benchling",
    "recursionpharmaceuticals",
    "generatebiomedicines",
    "xairatherapeutics",
    "evolutionaryscale",
]

LEVER_COMPANIES = [
    # None verified yet - add tokens here as you find them (check a
    # company's careers page for a "jobs.lever.co/COMPANY" URL).
]

# Workday-hosted companies. Unlike Greenhouse/Lever, Workday doesn't have
# one shared board format - each company has its own tenant + site name.
# Format: (tenant subdomain, wd cluster e.g. "wd1"/"wd5", site path segment)
WORKDAY_COMPANIES = [
    ("stryker", "wd1", "StrykerCareers"),
    ("illumina", "wd1", "illumina-universityrecruiting"),
    ("regeneron", "wd1", "Careers"),
    ("amgen", "wd1", "Careers"),
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

HEADERS = {
    "User-Agent": "internship-tracker/1.0 (personal project)",
    "Content-Type": "application/json",
}


def fetch_json(url, retries=2, delay=1.5, method="GET", body=None):
    for attempt in range(retries + 1):
        try:
            data_bytes = json.dumps(body).encode("utf-8") if body is not None else None
            req = Request(url, headers=HEADERS, data=data_bytes, method=method)
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


def scrape_workday(tenant, wd, site):
    url = f"https://{tenant}.{wd}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    body = {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": "intern"}
    data = fetch_json(url, method="POST", body=body)
    if not data or "jobPostings" not in data:
        return []

    results = []
    for job in data["jobPostings"]:
        title = job.get("title", "")
        if not INTERN_PATTERN.search(title):
            continue
        location = job.get("locationsText", "Unspecified")
        external_path = job.get("externalPath", "")
        full_url = f"https://{tenant}.{wd}.myworkdayjobs.com{external_path}"
        # Workday only gives a relative label like "Posted 3 Days Ago",
        # not an exact timestamp - stored as-is, the site displays it verbatim.
        posted_label = job.get("postedOn", "")
        results.append({
            "id": f"workday-{tenant}-{external_path}",
            "company": tenant,
            "title": title,
            "location": location,
            "url": full_url,
            "posted_at": posted_label,
            "source": "workday",
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

    print("Scraping Workday boards...")
    for tenant, wd, site in WORKDAY_COMPANIES:
        jobs = scrape_workday(tenant, wd, site)
        print(f"  {tenant}: {len(jobs)} internship postings")
        all_listings.extend(jobs)

    for listing in all_listings:
        listing["company"] = normalize_company_name(listing["company"])

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
