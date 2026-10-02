"""
Stage 5 — Phone Verification via Numverify
Input  : raw phone string from Google Maps
Output : validated phone, carrier, line type, country
"""

import os, re, requests, json, time
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

NUMVERIFY_KEY = os.getenv("NUMVERIFY_API_KEY")


def clean_phone(phone: str) -> str:
    """Strip formatting, keep digits and leading +."""
    if not phone:
        return ""
    cleaned = re.sub(r"[^\d+]", "", phone)
    # Add India country code if looks like local 10-digit number
    if re.match(r"^[6-9]\d{9}$", cleaned):
        cleaned = "+91" + cleaned
    return cleaned


def verify_phone(phone: str) -> dict:
    """Verify phone via Numverify API."""
    cleaned = clean_phone(phone)
    if not cleaned:
        return {"phone_valid": False, "phone_cleaned": "", "phone_carrier": "", "phone_line_type": ""}

    try:
        resp = requests.get(
            "http://apilayer.net/api/validate",
            params={
                "access_key": NUMVERIFY_KEY,
                "number": cleaned,
                "country_code": "",
                "format": 1
            },
            timeout=15
        )
        data = resp.json()

        if data.get("error"):
            print(f"    [numverify] API error: {data['error']}")
            return {"phone_valid": False, "phone_cleaned": cleaned, "phone_carrier": "", "phone_line_type": ""}

        return {
            "phone_valid":      data.get("valid", False),
            "phone_cleaned":    data.get("international_format", cleaned),
            "phone_local":      data.get("local_format", ""),
            "phone_carrier":    data.get("carrier", ""),
            "phone_line_type":  data.get("line_type", ""),
            "phone_country":    data.get("country_name", ""),
        }

    except Exception as e:
        print(f"    [numverify] request error: {e}")
        return {"phone_valid": False, "phone_cleaned": cleaned, "phone_carrier": "", "phone_line_type": ""}


def run_stage5(businesses: list[dict]) -> list[dict]:
    """Verify phones for all businesses."""
    print(f"\n[Stage 5] Verifying phones for {len(businesses)} businesses...")
    enriched = []

    for i, biz in enumerate(businesses):
        phone = biz.get("phone", "")
        print(f"  [{i+1}/{len(businesses)}] {biz['name']} | raw phone: {phone}")

        if phone:
            result = verify_phone(phone)
            biz.update(result)
            status = "✓ valid" if result["phone_valid"] else "✗ invalid"
            print(f"    {status} → {result.get('phone_cleaned', '')} ({result.get('phone_carrier', '')})")
        else:
            print(f"    [!] No phone number, skipping")
            biz["phone_valid"]     = False
            biz["phone_cleaned"]   = ""
            biz["phone_carrier"]   = ""
            biz["phone_line_type"] = ""

        enriched.append(biz)
        time.sleep(0.3)

    valid = sum(1 for b in enriched if b.get("phone_valid"))
    print(f"\n[Stage 5] Done — {valid}/{len(enriched)} phones verified")
    return enriched


if __name__ == "__main__":
    in_path  = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage4_owners.json')
    out_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'stage5_phones.json')

    with open(in_path) as f:
        businesses = json.load(f)

    enriched = run_stage5(businesses)

    with open(out_path, 'w') as f:
        json.dump(enriched, f, indent=2)
    print(f"\n[Stage 5] Saved → {out_path}")
