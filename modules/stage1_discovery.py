"""
Stage 1 — Business Discovery via SerpAPI (Google Maps)
Input : niche + city (user provided)
Output: list of businesses with name, address, phone, website, rating
"""

import os, requests, json, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SERPAPI_KEY = os.getenv("SERPAPI_KEY")


def discover_businesses(niche: str, city: str, limit: int = 20) -> list[dict]:
    """
    Search Google Maps for businesses matching niche + city.
    Returns list of raw business records.
    """
    print(f"\n[Stage 1] Discovering: '{niche}' in '{city}' (limit={limit})")
    results = []
    start = 0

    while len(results) < limit:
        params = {
            "engine": "google_maps",
            "q": f"{niche} in {city}",
            "type": "search",
            "api_key": SERPAPI_KEY,
            "start": start,
            "hl": "en",
        }

        try:
            resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
            data = resp.json()
        except Exception as e:
            print(f"  [!] SerpAPI request failed: {e}")
            break

        if "error" in data:
            print(f"  [!] SerpAPI error: {data['error']}")
            break

        places = data.get("local_results", [])
        if not places:
            print(f"  [!] No more results at offset {start}")
            break

        for place in places:
            if len(results) >= limit:
                break

            biz = {
                "name":        place.get("title", ""),
                "address":     place.get("address", ""),
                "phone":       place.get("phone", ""),
                "website":     place.get("website", ""),
                "rating":      place.get("rating", ""),
                "reviews":     place.get("reviews", ""),
                "category":    place.get("type", ""),
                "maps_url":    place.get("link", ""),
                "place_id":    place.get("place_id", ""),
                "niche":       niche,
                "city":        city,
            }
            results.append(biz)
            print(f"  ✓ [{len(results)}] {biz['name']} | {biz['phone']} | {biz['website']}")

        start += len(places)
        if len(places) < 20:
            break
        time.sleep(0.5)

    print(f"\n[Stage 1] Done — {len(results)} businesses found")
    return results


if __name__ == "__main__":
    import sys
    niche = input("Enter niche (e.g. dental clinics): ").strip()
    city  = input("Enter city  (e.g. Mumbai):          ").strip()
    limit = int(input("How many leads? (default 20):      ").strip() or "20")

    results = discover_businesses(niche, city, limit)

    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage1_raw.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n[Stage 1] Saved → {out_path}")
