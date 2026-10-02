"""
Stage 7 — Export
Produces a clean CSV of all leads sorted by ICP score.
Fields match the final lead record spec from research.
"""

import os, json, csv
from dotenv import load_dotenv
from datetime import datetime

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

FIELDS = [
    # Identity
    "name", "category", "niche", "city",
    # Contact
    "website", "phone_cleaned", "phone_valid", "phone_carrier",
    "email", "email_confidence", "email_source",
    # Owner
    "owner_name", "owner_title", "owner_linkedin",
    # Quality signals
    "rating", "reviews", "maps_url",
    # ICP
    "icp_score", "icp_tier", "icp_reasoning", "outreach_angle",
    "icp_missing",
]


def export_csv(businesses: list[dict], out_path: str):
    """Write final lead CSV."""
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        for biz in businesses:
            row = {k: biz.get(k, "") for k in FIELDS}
            # Flatten lists
            if isinstance(row.get("icp_missing"), list):
                row["icp_missing"] = ", ".join(row["icp_missing"])
            writer.writerow(row)
    print(f"[Export] CSV saved → {out_path}")


def print_summary(businesses: list[dict]):
    """Print pipeline summary stats."""
    total  = len(businesses)
    hot    = sum(1 for b in businesses if b.get("icp_tier") == "Hot")
    warm   = sum(1 for b in businesses if b.get("icp_tier") == "Warm")
    cold   = sum(1 for b in businesses if b.get("icp_tier") == "Cold")
    emails = sum(1 for b in businesses if b.get("email"))
    phones = sum(1 for b in businesses if b.get("phone_valid"))
    owners = sum(1 for b in businesses if b.get("owner_name"))

    print("\n" + "="*50)
    print("  PIPELINE COMPLETE — SUMMARY")
    print("="*50)
    print(f"  Total leads:       {total}")
    print(f"  🔥 Hot (8-10):     {hot}")
    print(f"  🟡 Warm (5-7):     {warm}")
    print(f"  🔵 Cold (1-4):     {cold}")
    print(f"  📧 Emails found:   {emails}/{total}")
    print(f"  📞 Phones valid:   {phones}/{total}")
    print(f"  👤 Owners found:   {owners}/{total}")
    print("="*50)

    if businesses:
        print("\n  TOP 5 LEADS:")
        for i, b in enumerate(businesses[:5]):
            print(f"\n  [{i+1}] {b.get('name','')}")
            print(f"       Score : {b.get('icp_score',0)}/10 {b.get('icp_tier','')}")
            print(f"       Email : {b.get('email','—')}")
            print(f"       Owner : {b.get('owner_name','—')} ({b.get('owner_title','—')})")
            print(f"       Phone : {b.get('phone_cleaned','—')}")
            print(f"       Hook  : {b.get('outreach_angle','—')}")


if __name__ == "__main__":
    in_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage6_scored.json')
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = os.path.join(os.path.dirname(__file__), '..', 'output', f'leads_{ts}.csv')

    with open(in_path) as f:
        businesses = json.load(f)

    print_summary(businesses)
    export_csv(businesses, out_csv)
