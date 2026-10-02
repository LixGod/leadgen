"""
Stage 4 — Owner Name Enrichment via Apollo.io
Input  : business domain
Output : owner name, title, linkedin URL
Strategy: domain → Apollo people search → pick decision maker by seniority
"""

import os, re, requests, json, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

APOLLO_KEY = os.getenv("APOLLO_API_KEY")

# Seniority ranking — higher = more likely the owner/decision maker
SENIORITY_RANK = {
    "owner": 10, "founder": 10, "co-founder": 10, "proprietor": 10,
    "ceo": 9, "chief executive": 9, "managing director": 9, "md": 8,
    "director": 7, "president": 7, "partner": 6, "head": 5,
    "manager": 4, "lead": 3, "senior": 2,
}


def score_title(title: str) -> int:
    t = title.lower()
    for kw, score in SENIORITY_RANK.items():
        if kw in t:
            return score
    return 0


def apollo_people_search(domain: str) -> list[dict]:
    """Search Apollo for people at this domain."""
    try:
        resp = requests.post(
            "https://api.apollo.io/v1/mixed_people/search",
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": APOLLO_KEY,
            },
            json={
                "q_organization_domains": domain,
                "page": 1,
                "per_page": 10,
                "prospected_by_current_team": ["no"],
            },
            timeout=20
        )
        data = resp.json()
        return data.get("people", [])
    except Exception as e:
        print(f"    [apollo] search error: {e}")
        return []


def pick_decision_maker(people: list[dict]) -> dict | None:
    """Pick the most senior person from Apollo results."""
    if not people:
        return None

    scored = []
    for p in people:
        title = p.get("title", "") or ""
        name  = f"{p.get('first_name', '')} {p.get('last_name', '')}".strip()
        if not name:
            continue
        scored.append({
            "owner_name":     name,
            "owner_title":    title,
            "owner_linkedin": p.get("linkedin_url", ""),
            "owner_email":    p.get("email", ""),
            "_score":         score_title(title),
        })

    if not scored:
        return None

    return max(scored, key=lambda x: x["_score"])


def run_stage4(businesses: list[dict]) -> list[dict]:
    """Enrich each business with Apollo owner data."""
    print(f"\n[Stage 4] Owner enrichment via Apollo for {len(businesses)} businesses...")
    enriched = []

    for i, biz in enumerate(businesses):
        print(f"\n  [{i+1}/{len(businesses)}] {biz['name']}")

        # Skip if owner already found from scrape or email API
        if biz.get("owner_name") and len(biz["owner_name"].split()) >= 2:
            print(f"    ✓ Owner already known: {biz['owner_name']}, skipping Apollo")
            enriched.append(biz)
            continue

        # Extract domain
        website = biz.get("website", "")
        domain  = re.sub(r"https?://(www\.)?", "", website).split("/")[0] if website else ""

        if not domain:
            print(f"    [!] No domain, skipping Apollo")
            enriched.append(biz)
            continue

        print(f"    → Apollo search: {domain}")
        people = apollo_people_search(domain)
        print(f"    → {len(people)} people found")

        dm = pick_decision_maker(people)
        if dm:
            biz["owner_name"]     = dm["owner_name"]
            biz["owner_title"]    = dm["owner_title"]
            biz["owner_linkedin"] = dm["owner_linkedin"]
            # Use Apollo email if we don't have one yet
            if not biz.get("email") and dm.get("owner_email"):
                biz["email"] = dm["owner_email"]
            print(f"    ✓ Owner: {dm['owner_name']} | {dm['owner_title']}")
        else:
            print(f"    [!] No decision maker found")
            biz.setdefault("owner_name", "")
            biz.setdefault("owner_title", "")
            biz.setdefault("owner_linkedin", "")

        enriched.append(biz)
        time.sleep(0.8)  # Apollo rate limit

    found = sum(1 for b in enriched if b.get("owner_name"))
    print(f"\n[Stage 4] Done — {found}/{len(enriched)} owners found")
    return enriched


if __name__ == "__main__":
    in_path  = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage3_emails.json')
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage4_owners.json')

    with open(in_path) as f:
        businesses = json.load(f)

    enriched = run_stage4(businesses)

    with open(out_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    print(f"\n[Stage 4] Saved → {out_path}")
