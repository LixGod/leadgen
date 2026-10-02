"""
Stage 6 — ICP Scoring via Groq (llama-3.3-70b)
Input  : full enriched lead record
Output : ICP score 1-10, reasoning, priority tier (Hot/Warm/Cold)
"""

import os, json, time, requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

GROQ_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL    = "llama-3.3-70b-versatile"


SCORING_PROMPT = """You are a B2B lead qualification expert. Score this business lead for outreach potential.

Lead data:
{lead_json}

Score this lead from 1-10 based on:
- Has a working website (2 pts)
- Has a verified email (2 pts)  
- Has owner/decision maker name (2 pts)
- Has valid phone (1 pt)
- Business appears active (reviews/rating) (1 pt)
- Business size suggests budget for services (1 pt)
- Contact info completeness (1 pt)

Respond with ONLY valid JSON, no markdown, no explanation outside the JSON:
{{
  "score": <1-10 integer>,
  "tier": "<Hot|Warm|Cold>",
  "reasoning": "<1 sentence why>",
  "missing": ["<list of missing fields>"],
  "outreach_angle": "<1 sentence personalized hook for cold outreach>"
}}

Rules:
- Hot = score 8-10 (has email + owner name + phone)
- Warm = score 5-7 (has 2 of the 3 above)
- Cold = score 1-4 (missing most contact info)"""


def score_lead(biz: dict) -> dict:
    """Score a single lead via Groq."""

    # Build a clean subset for the prompt (avoid sending huge about_text)
    lead_for_prompt = {
        "name":          biz.get("name", ""),
        "category":      biz.get("category", ""),
        "city":          biz.get("city", ""),
        "website":       biz.get("website", ""),
        "phone":         biz.get("phone_cleaned") or biz.get("phone", ""),
        "phone_valid":   biz.get("phone_valid", False),
        "email":         biz.get("email", ""),
        "owner_name":    biz.get("owner_name", ""),
        "owner_title":   biz.get("owner_title", ""),
        "rating":        biz.get("rating", ""),
        "reviews":       biz.get("reviews", ""),
        "has_linkedin":  bool(biz.get("owner_linkedin", "")),
    }

    prompt = SCORING_PROMPT.format(lead_json=json.dumps(lead_for_prompt, indent=2))

    try:
        resp = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 300,
            },
            timeout=20
        )
        content = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip markdown fences if present
        content = content.replace("```json", "").replace("```", "").strip()
        scored  = json.loads(content)
        return scored

    except Exception as e:
        print(f"    [groq] scoring error: {e}")
        return {"score": 0, "tier": "Cold", "reasoning": "Scoring failed", "missing": [], "outreach_angle": ""}


def run_stage6(businesses: list[dict]) -> list[dict]:
    """Score all leads for ICP fit."""
    print(f"\n[Stage 6] ICP scoring {len(businesses)} leads via Groq...")
    scored = []

    for i, biz in enumerate(businesses):
        print(f"  [{i+1}/{len(businesses)}] {biz['name']}")
        result = score_lead(biz)

        biz["icp_score"]       = result.get("score", 0)
        biz["icp_tier"]        = result.get("tier", "Cold")
        biz["icp_reasoning"]   = result.get("reasoning", "")
        biz["icp_missing"]     = result.get("missing", [])
        biz["outreach_angle"]  = result.get("outreach_angle", "")

        tier_icon = {"Hot": "🔥", "Warm": "🟡", "Cold": "🔵"}.get(biz["icp_tier"], "")
        print(f"    {tier_icon} Score: {biz['icp_score']}/10 ({biz['icp_tier']}) — {biz['icp_reasoning']}")

        scored.append(biz)
        time.sleep(0.2)  # Groq is fast, small delay to be safe

    # Sort by score descending
    scored.sort(key=lambda x: x.get("icp_score", 0), reverse=True)

    hot  = sum(1 for b in scored if b.get("icp_tier") == "Hot")
    warm = sum(1 for b in scored if b.get("icp_tier") == "Warm")
    cold = sum(1 for b in scored if b.get("icp_tier") == "Cold")
    print(f"\n[Stage 6] Done — 🔥 Hot: {hot} | 🟡 Warm: {warm} | 🔵 Cold: {cold}")
    return scored


if __name__ == "__main__":
    in_path  = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage5_phones.json')
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage6_scored.json')

    with open(in_path) as f:
        businesses = json.load(f)

    scored = run_stage6(businesses)

    with open(out_path, 'w') as f:
        json.dump(scored, f, indent=2)
    print(f"\n[Stage 6] Saved → {out_path}")
