"""
Stage 3 — Email Finding
Primary : Snov.io domain search
Fallback: Hunter.io domain search
Input   : business domain
Output  : work email + confidence score
"""

import os, re, requests, json, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SNOV_KEY   = os.getenv("SNOV_API_KEY")
HUNTER_KEY = os.getenv("HUNTER_API_KEY")


def extract_domain(website: str) -> str | None:
    """Extract clean domain from URL."""
    if not website:
        return None
    website = re.sub(r"https?://", "", website).strip("/")
    website = website.split("/")[0].split("?")[0]
    # Remove www.
    website = re.sub(r"^www\.", "", website)
    return website if "." in website else None


# ── Snov.io ────────────────────────────────────────────────────────────────

def snov_get_access_token() -> str | None:
    """Get Snov.io OAuth access token."""
    try:
        resp = requests.post(
            "https://api.snov.io/v1/oauth/access_token",
            json={"grant_type": "client_credentials", "client_id": SNOV_KEY, "client_secret": SNOV_KEY},
            timeout=15
        )
        return resp.json().get("access_token")
    except Exception as e:
        print(f"    [snov] token error: {e}")
        return None


def snov_find_emails(domain: str) -> list[dict]:
    """Find emails for a domain via Snov.io."""
    token = snov_get_access_token()
    if not token:
        return []
    try:
        resp = requests.post(
            "https://api.snov.io/v2/domain-emails-with-info",
            json={"access_token": token, "domain": domain, "type": "all", "limit": 5},
            timeout=15
        )
        data = resp.json()
        emails = data.get("emails", [])
        return [{"email": e.get("email"), "confidence": e.get("confidence", 0),
                 "first_name": e.get("firstName", ""), "last_name": e.get("lastName", ""),
                 "position": e.get("position", ""), "source": "snov"} for e in emails]
    except Exception as e:
        print(f"    [snov] search error: {e}")
        return []


# ── Hunter.io ──────────────────────────────────────────────────────────────

def hunter_find_emails(domain: str) -> list[dict]:
    """Find emails for a domain via Hunter.io."""
    try:
        resp = requests.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": HUNTER_KEY, "limit": 5},
            timeout=15
        )
        data = resp.json()
        emails_raw = data.get("data", {}).get("emails", [])
        return [{"email": e.get("value"), "confidence": e.get("confidence", 0),
                 "first_name": e.get("first_name", ""), "last_name": e.get("last_name", ""),
                 "position": e.get("position", ""), "source": "hunter"} for e in emails_raw]
    except Exception as e:
        print(f"    [hunter] search error: {e}")
        return []


# ── Main ───────────────────────────────────────────────────────────────────

def find_email_for_domain(domain: str) -> dict:
    """Try Snov first, fall back to Hunter."""
    print(f"    → Snov.io search for: {domain}")
    emails = snov_find_emails(domain)

    if not emails:
        print(f"    → Snov empty, trying Hunter.io...")
        emails = hunter_find_emails(domain)

    if not emails:
        return {"email": "", "email_confidence": 0, "owner_first": "", "owner_last": "", "owner_title": ""}

    # Pick highest confidence
    best = max(emails, key=lambda e: e.get("confidence", 0))
    print(f"    ✓ Email: {best['email']} (confidence: {best['confidence']}) via {best['source']}")
    return {
        "email":             best["email"],
        "email_confidence":  best["confidence"],
        "email_source":      best["source"],
        "owner_first":       best["first_name"],
        "owner_last":        best["last_name"],
        "owner_title":       best["position"],
    }


def run_stage3(businesses: list[dict]) -> list[dict]:
    """Enrich each business with found emails."""
    print(f"\n[Stage 3] Finding emails for {len(businesses)} businesses...")
    enriched = []

    for i, biz in enumerate(businesses):
        print(f"\n  [{i+1}/{len(businesses)}] {biz['name']}")

        # Skip if we already have a good email from scraping
        if biz.get("email") and "@" in biz["email"]:
            print(f"    ✓ Already have email from scrape: {biz['email']}, skipping API call")
            enriched.append(biz)
            continue

        domain = extract_domain(biz.get("website", ""))
        if not domain:
            print(f"    [!] No domain available, skipping")
            biz["email_confidence"] = 0
            enriched.append(biz)
            continue

        result = find_email_for_domain(domain)
        biz.update(result)

        # If email from API and no owner name yet, use API result
        if not biz.get("owner_name") and result.get("owner_first"):
            biz["owner_name"] = f"{result['owner_first']} {result['owner_last']}".strip()

        enriched.append(biz)
        time.sleep(0.5)

    found = sum(1 for b in enriched if b.get("email"))
    print(f"\n[Stage 3] Done — {found}/{len(enriched)} emails found")
    return enriched


if __name__ == "__main__":
    in_path  = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage2_scraped.json')
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage3_emails.json')

    with open(in_path) as f:
        businesses = json.load(f)

    enriched = run_stage3(businesses)

    with open(out_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    print(f"\n[Stage 3] Saved → {out_path}")
