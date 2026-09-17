"""
Cloudflare API Token ကို verify လုပ်ကြည့်မယ့် Script
------------------------------------------------------
Token ကိုယ်တိုင် valid ဖြစ်မဖြစ်၊ ဘယ် permission တွေရှိလဲ စစ်ဖို့
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

print(f"[Debug] Loaded API_TOKEN: {API_TOKEN[:6]}...{API_TOKEN[-4:]}" if API_TOKEN else "[Debug] API_TOKEN not found in .env")

response = requests.get(
    "https://api.cloudflare.com/client/v4/user/tokens/verify",
    headers={"Authorization": f"Bearer {API_TOKEN}"},
)

print("Status Code:", response.status_code)
print("Response:", response.json())