"""
Cloudflare Audit Log ကို API ကနေဆွဲယူမယ့် Script
--------------------------------------------------
Requirement: pip install -r requirements.txt
Config: .env file ထဲမှာ credentials များ ထည့်ပါ (.env.example ကို copy ကူးပါ)
"""

import os
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# .env file ထဲက value များကို environment ထဲသို့ load လုပ်ခြင်း
load_dotenv()

# ---------------------------
# .env ထဲက Config များ ဖတ်ခြင်း
# ---------------------------
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
ZONE_ID = os.getenv("CLOUDFLARE_ZONE_ID")          # audit log အတွက်တော့ မလိုပေမယ့် အသင့်ထားပါတယ်
API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/audit_logs"

print(f"[Debug] Loaded ACCOUNT_ID: {ACCOUNT_ID}")

HEADERS = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json",
}


def check_config():
    missing = [
        name
        for name, value in [
            ("CLOUDFLARE_ACCOUNT_ID", ACCOUNT_ID),
            ("CLOUDFLARE_API_TOKEN", API_TOKEN),
        ]
        if not value
    ]
    if missing:
        raise SystemExit(
            ".env file ထဲမှာ အောက်ပါ value(s) များ ပျောက်နေပါတယ်: "
            + ", ".join(missing)
            + "\n.env.example ကို .env အဖြစ် copy ကူးပြီး ဖြည့်ပါ။"
        )


def fetch_audit_logs(days_back=7, per_page=100):
    """
    လွန်ခဲ့သော days_back ရက်အတွင်း audit log များကို
    pagination နဲ့ တစ်ခါတည်း အကုန်ဆွဲယူမယ့် function
    """
    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days_back)).strftime("%Y-%m-%dT%H:%M:%SZ")
    before = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    all_logs = []
    page = 1

    while True:
        params = {
            "since": since,
            "before": before,
            "page": page,
            "per_page": per_page,
        }

        response = requests.get(BASE_URL, headers=HEADERS, params=params)

        if response.status_code != 200:
            print(f"Error {response.status_code}: {response.text}")
            break

        data = response.json()

        if not data.get("success", False):
            print("API Error:", data.get("errors"))
            break

        result = data.get("result", [])
        all_logs.extend(result)

        result_info = data.get("result_info", {})
        total_pages = result_info.get("total_pages", 1)

        print(f"Page {page}/{total_pages} - {len(result)} logs fetched")

        if page >= total_pages or not result:
            break

        page += 1

    return all_logs


def save_to_file(logs, filename="audit_logs.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
    print(f"\nTotal {len(logs)} logs saved to {filename}")


if __name__ == "__main__":
    check_config()
    logs = fetch_audit_logs(days_back=7)   # လွန်ခဲ့သော ၇ ရက်စာ ဆွဲမယ်
    save_to_file(logs)