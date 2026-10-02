#!/usr/bin/env python3
"""
Lead Generation Pipeline — Main Runner
Orchestrates all 7 stages end to end.

Usage:
    python run_pipeline.py
    python run_pipeline.py --niche "dental clinics" --city "Mumbai" --limit 50
    python run_pipeline.py --resume-from 3   (skip to stage 3, load stage 2 output)
"""

import os, sys, json, argparse
from datetime import datetime

# Add modules to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from stage1_discovery       import discover_businesses
from stage2_scraper         import run_stage2
from stage3_email_finder    import run_stage3
from stage4_owner_enrichment import run_stage4
from stage5_phone_verify    import run_stage5
from stage6_icp_scorer      import run_stage6
from stage7_export          import export_csv, print_summary

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
STAGE_FILES = {
    1: "stage1_raw.json",
    2: "stage2_scraped.json",
    3: "stage3_emails.json",
    4: "stage4_owners.json",
    5: "stage5_phones.json",
    6: "stage6_scored.json",
}


def save_stage(data: list[dict], stage: int):
    path = os.path.join(OUTPUT_DIR, STAGE_FILES[stage])
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"\n  💾 Stage {stage} saved → {path}")


def load_stage(stage: int) -> list[dict]:
    path = os.path.join(OUTPUT_DIR, STAGE_FILES[stage])
    with open(path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Lead Generation Pipeline")
    parser.add_argument("--niche",        type=str, default="", help="Business niche (e.g. 'dental clinics')")
    parser.add_argument("--city",         type=str, default="", help="Target city (e.g. 'Mumbai')")
    parser.add_argument("--limit",        type=int, default=20,  help="Number of leads to discover (default: 20)")
    parser.add_argument("--resume-from",  type=int, default=1,   help="Resume from stage N (loads previous stage output)")
    parser.add_argument("--skip-scrape",  action="store_true",   help="Skip website scraping (stage 2)")
    args = parser.parse_args()

    print("\n" + "="*55)
    print("  🚀 LEAD GENERATION PIPELINE")
    print("="*55)

    # ── Get niche + city if not provided ──────────────────────
    niche = args.niche
    city  = args.city

    if not niche:
        niche = input("\n  Enter niche (e.g. 'dental clinics', 'CA firms'): ").strip()
    if not city:
        city  = input("  Enter city  (e.g. 'Mumbai', 'Bangalore'):          ").strip()
    if not niche or not city:
        print("  [!] Niche and city are required. Exiting.")
        sys.exit(1)

    limit = args.limit
    if limit == 20 and "--limit" not in sys.argv:
        try:
            inp = input(f"  How many leads? (default 20): ").strip()
            if inp:
                limit = int(inp)
        except:
            pass

    resume_from = args.resume_from
    print(f"\n  Niche  : {niche}")
    print(f"  City   : {city}")
    print(f"  Limit  : {limit}")
    print(f"  Starting from stage: {resume_from}")
    print("="*55)

    # ── Stage 1: Discovery ────────────────────────────────────
    if resume_from <= 1:
        businesses = discover_businesses(niche, city, limit)
        save_stage(businesses, 1)
    else:
        print("\n[Stage 1] Skipping — loading from file...")
        businesses = load_stage(1)

    if not businesses:
        print("\n[!] No businesses found. Exiting.")
        sys.exit(1)

    # ── Stage 2: Website Scraping ─────────────────────────────
    if resume_from <= 2 and not args.skip_scrape:
        businesses = run_stage2(businesses)
        save_stage(businesses, 2)
    elif args.skip_scrape:
        print("\n[Stage 2] Skipped (--skip-scrape flag)")
    else:
        print("\n[Stage 2] Skipping — loading from file...")
        businesses = load_stage(2)

    # ── Stage 3: Email Finding ────────────────────────────────
    if resume_from <= 3:
        businesses = run_stage3(businesses)
        save_stage(businesses, 3)
    else:
        print("\n[Stage 3] Skipping — loading from file...")
        businesses = load_stage(3)

    # ── Stage 4: Owner Enrichment ─────────────────────────────
    if resume_from <= 4:
        businesses = run_stage4(businesses)
        save_stage(businesses, 4)
    else:
        print("\n[Stage 4] Skipping — loading from file...")
        businesses = load_stage(4)

    # ── Stage 5: Phone Verification ───────────────────────────
    if resume_from <= 5:
        businesses = run_stage5(businesses)
        save_stage(businesses, 5)
    else:
        print("\n[Stage 5] Skipping — loading from file...")
        businesses = load_stage(5)

    # ── Stage 6: ICP Scoring ──────────────────────────────────
    if resume_from <= 6:
        businesses = run_stage6(businesses)
        save_stage(businesses, 6)
    else:
        print("\n[Stage 6] Skipping — loading from file...")
        businesses = load_stage(6)

    # ── Stage 7: Export ───────────────────────────────────────
    print_summary(businesses)
    ts      = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_csv = os.path.join(OUTPUT_DIR, f"leads_{niche.replace(' ','_')}_{city}_{ts}.csv")
    export_csv(businesses, out_csv)

    print(f"\n  ✅ Done! Leads saved to:\n     {out_csv}\n")


if __name__ == "__main__":
    main()
