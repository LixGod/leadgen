"""
Stage 2 — Website Scraping
Primary  : scrape.do (proxy) + direct HTML parse
Fallback : Firecrawl API
Extracts : emails (regex), /about page content, owner name hints
"""

import os, re, requests, json, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SCRAPE_DO_KEY   = os.getenv("SCRAPE_DO_API_KEY")
FIRECRAWL_KEY   = os.getenv("FIRECRAWL_API_KEY")

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"[\+\(]?[0-9][0-9 \-\(\)]{7,}[0-9]")

ABOUT_SLUGS = ["/about", "/about-us", "/team", "/our-team", "/contact", "/contact-us"]


def scrape_with_scrapedo(url: str) -> str | None:
    """Route URL through scrape.do for JS rendering + proxy."""
    try:
        resp = requests.get(
            "https://api.scrape.do",
            params={"token": SCRAPE_DO_KEY, "url": url, "render": "true"},
            timeout=30
        )
        if resp.status_code == 200:
            return resp.text
    except Exception as e:
        print(f"    [scrape.do] failed for {url}: {e}")
    return None


def scrape_with_firecrawl(url: str) -> str | None:
    """Firecrawl fallback — better for complex JS-heavy sites."""
    try:
        resp = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {FIRECRAWL_KEY}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"]},
            timeout=30
        )
        data = resp.json()
        if data.get("success"):
            return data.get("data", {}).get("markdown", "")
    except Exception as e:
        print(f"    [firecrawl] failed for {url}: {e}")
    return None


def extract_emails(text: str) -> list[str]:
    found = EMAIL_RE.findall(text)
    # Filter out common non-emails
    filtered = [e for e in found if not any(skip in e.lower() for skip in
        ["example", "youremail", "domain", "email@", "@email", "test@", "@test", ".png", ".jpg"])]
    return list(dict.fromkeys(filtered))  # deduplicate, preserve order


def extract_owner_hints(text: str) -> str:
    """Extract sentences likely to contain owner/founder names."""
    hints = []
    patterns = [
        r"(?:founded by|owner|director|ceo|managing director|proprietor|partner|head of)[:\s]+([A-Z][a-z]+ [A-Z][a-z]+)",
        r"([A-Z][a-z]+ [A-Z][a-z]+)(?:\s+is the|\s+,?\s+(?:founder|owner|director|ceo|head))",
    ]
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        hints.extend(matches)
    return ", ".join(dict.fromkeys(hints)) if hints else ""


def scrape_website(website: str) -> dict:
    """
    Scrape a business website.
    Returns: emails, about_text, owner_hint
    """
    result = {"emails": [], "about_text": "", "owner_hint": "", "scraped_url": website}

    if not website or not website.startswith("http"):
        website = "https://" + website.lstrip("/")

    # 1. Scrape homepage
    print(f"    → Scraping homepage: {website}")
    html = scrape_with_scrapedo(website)
    if not html:
        print(f"    → scrape.do failed, trying Firecrawl...")
        html = scrape_with_firecrawl(website)

    if html:
        result["emails"] = extract_emails(html)
        result["owner_hint"] = extract_owner_hints(html)

    # 2. Try /about page if no email found yet
    if not result["emails"]:
        base = website.rstrip("/")
        for slug in ABOUT_SLUGS:
            about_url = base + slug
            print(f"    → Trying about page: {about_url}")
            about_html = scrape_with_scrapedo(about_url)
            if not about_html:
                about_html = scrape_with_firecrawl(about_url)
            if about_html:
                emails = extract_emails(about_html)
                if emails:
                    result["emails"] = emails
                    result["about_text"] = about_html[:2000]  # first 2000 chars
                hint = extract_owner_hints(about_html)
                if hint:
                    result["owner_hint"] = hint
                if result["emails"] and result["owner_hint"]:
                    break
            time.sleep(0.3)

    print(f"    ✓ Emails found: {result['emails']} | Owner hint: {result['owner_hint']}")
    return result


def run_stage2(businesses: list[dict]) -> list[dict]:
    """Enrich each business with scraped website data."""
    print(f"\n[Stage 2] Scraping websites for {len(businesses)} businesses...")
    enriched = []

    for i, biz in enumerate(businesses):
        print(f"\n  [{i+1}/{len(businesses)}] {biz['name']}")
        website = biz.get("website", "")

        if website:
            scraped = scrape_website(website)
            biz["emails_from_site"]  = scraped["emails"]
            biz["email"]             = scraped["emails"][0] if scraped["emails"] else ""
            biz["owner_hint"]        = scraped["owner_hint"]
            biz["about_text"]        = scraped["about_text"]
        else:
            print(f"    [!] No website found, skipping scrape")
            biz["emails_from_site"]  = []
            biz["email"]             = ""
            biz["owner_hint"]        = ""
            biz["about_text"]        = ""

        enriched.append(biz)
        time.sleep(0.5)

    print(f"\n[Stage 2] Done — {sum(1 for b in enriched if b['email'])} emails found")
    return enriched


if __name__ == "__main__":
    in_path  = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage1_raw.json')
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage2_scraped.json')

    with open(in_path) as f:
        businesses = json.load(f)

    enriched = run_stage2(businesses)

    with open(out_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    print(f"\n[Stage 2] Saved → {out_path}")
