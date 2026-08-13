#!/usr/bin/env python3
"""
Internship scraper for Jayden's tracker.

Pulls live listings from public Greenhouse, Lever, Ashby, and Workday
job-board APIs for a curated list of bioengineering / biotech / medtech
companies, filters for internship roles, tags them by relevance to
Jayden's resume skills, and writes the result to data/listings.json.

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

GREENHOUSE_COMPANIES = [
    "ginkgobioworks",
    "10xgenomics",
    "benchling",
    "recursionpharmaceuticals",
    "generatebiomedicines",
    "xairatherapeutics",
    "evolutionaryscale",
    "colossalbiosciences",
    "neuralink",
    "formlabs",
]

LEVER_COMPANIES = [
    # None verified yet - add tokens here as you find them (check a
    # company's careers page for a "jobs.lever.co/COMPANY" URL).
]

ASHBY_COMPANIES = [
    "iambic-therapeutics",
    "basecamp-research",
    "cradlebio",
]

WORKDAY_COMPANIES = [
    ("stryker", "wd1", "StrykerCareers"),
    ("illumina", "wd1", "illumina-universityrecruiting"),
    ("regeneron", "wd1", "Careers"),
    ("amgen", "wd1", "Careers"),
    ("edwards", "wd5", "edwardscareers"),
    ("dexcom", "wd1", "Dexcom"),
    ("medtronic", "wd1", "MedtronicCareers"),
]

RESUME_KEYWORDS = [
    "bioengineering", "biomedical", "biotech", "biotechnology",
    "medical device", "hardware", "embedded", "firmware", "arduino",
    "cad", "sensor", "wearable", "automation", "lab", "research",
    "computational", "hpc", "protein", "python", "prototyp",
]

INTERN_PATTERN = re.compile(r"\bintern(ship)?\b", re.IGNORECASE)

BLOCKED_LOCATION_KEYWORDS = [
    "india", "china", "singapore", "japan", "australia", "brazil", "mexico",
    "south korea", "korea", "israel", "uae", "dubai", "hong kong", "taiwan",
    "vietnam", "philippines", "indonesia", "malaysia", "thailand",
    "pakistan", "bangladesh", "new zealand", "south africa", "nigeria",
    "egypt", "saudi", "qatar", "kuwait", "argentina", "chile", "colombia",
    "peru", "russia",
]

EXCLUDE_TITLE_KEYWORDS = [
    "mba", "sales", "commercial", "marketing", "finance", "financial",
    "account executive", "account manager", "business development",
    "communications", "human resources", "recruiting", "recruiter",
    "legal", "customer success", "talent acquisition", "public relations",
    "investor relations", "procurement",
]


def is_blocked_location(location):
    loc = location.lower()
    return any(kw in loc for kw in BLOCKED_LOCATION_KEYWORDS)


def is_off_field_title(title):
    t = title.lower()
    return any(kw in t for kw in EXCLUDE_TITLE_KEYWORDS)


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
    return [kw for kw in RESUME_KEYWORDS if kw in text]


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


def scrape_ashby(token):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=false"
    data = fetch_json(url)
    if not data or "jobs" not in data:
        return []
    results = []
    for job in data["jobs"]:
        title = job.get("title", "")
        if not INTERN_PATTERN.search(title):
            continue
        location = job.get("location") or job.get("locationName") or "Unspecified"
        job_url = job.get("jobUrl") or job.get("applyUrl") or f"https://jobs.ashbyhq.com/{token}"
        results.append({
            "id": f"ashby-{token}-{job.get('id')}",
            "company": token,
            "title": title,
            "location": location,
            "url": job_url,
            "posted_at": job.get("publishedAt", ""),
            "source": "ashby",
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

    print("Scraping Ashby boards...")
    for token in ASHBY_COMPANIES:
        jobs = scrape_ashby(token)
        print(f"  {token}: {len(jobs)} internship postings")
        all_listings.extend(jobs)

    print("Scraping Workday boards...")
    for tenant, wd, site in WORKDAY_COMPANIES:
        jobs = scrape_workday(tenant, wd, site)
        print(f"  {tenant}: {len(jobs)} internship postings")
        all_listings.extend(jobs)

    before_filter = len(all_listings)
    all_listings = [
        listing for listing in all_listings
        if not is_blocked_location(listing["location"])
        and not is_off_field_title(listing["title"])
    ]
    print(f"\nFiltered out {before_filter - len(all_listings)} listings "
          f"(off-field titles or unwanted locations)")

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
