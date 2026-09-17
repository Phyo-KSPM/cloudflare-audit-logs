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
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
)

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


def fetch_audit_logs(since=None, before=None, days_back=None, per_page=100):
    """
    Audit log များကို pagination နဲ့ တစ်ခါတည်း အကုန်ဆွဲယူမယ့် function

    ၂ မျိုးထဲက တစ်မျိုးကို ရွေးသုံးနိုင်ပါတယ်:
      1) days_back=7  → "လွန်ခဲ့သော N ရက်" ပုံစံ
      2) since="2026-08-16T00:00:00Z", before="2026-08-17T00:00:00Z"
         → တိတိကျကျ ရက်စွဲအပိုင်းအခြား ပုံစံ (Aug 16 2026 ရဲ့ log အတွက် ဒါကိုသုံးပါ)
    """
    if since is None or before is None:
        now = datetime.now(timezone.utc)
        since = (now - timedelta(days=days_back or 7)).strftime("%Y-%m-%dT%H:%M:%SZ")
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


def _mask(value, keep_start=6, keep_end=4):
    """Account/Zone ID လို sensitive value ကို တစ်စိတ်တစ်ပိုင်း ဖုံးပေးမယ့် helper"""
    if not value or not isinstance(value, str) or len(value) <= keep_start + keep_end:
        return value or ""
    return f"{value[:keep_start]}...{value[-keep_end:]}"


def _format_entry(log):
    """audit log entry တစ်ခုကို PDF row အတွက် readable field များ ဖြစ်အောင် ပြောင်းခြင်း"""
    when = log.get("when", "")
    actor = log.get("actor", {}) or {}
    action = log.get("action", {}) or {}
    resource = log.get("resource", {}) or {}
    metadata = log.get("metadata", {}) or {}
    owner = log.get("owner", {}) or {}

    actor_desc = actor.get("email") or actor.get("type") or actor.get("id", "-")
    action_desc = action.get("description") or action.get("info") or action.get("type", "-")
    result = "Success" if action.get("result") in (True, "success") else str(action.get("result", "-"))
    resource_type = resource.get("type", "-")
    zone_name = metadata.get("zone_name", "-")
    account_id = _mask(owner.get("id", ""))

    return {
        "when": when,
        "actor": actor_desc,
        "action": action_desc,
        "result": result,
        "resource_type": resource_type,
        "zone_name": zone_name,
        "account_id": account_id,
    }


def save_to_pdf(logs, filename="audit_report.pdf", title="Cloudflare Audit Log Report"):
    """
    Audit log များကို လူဖတ်လို့ ရအောင် ဇယားပုံစံနဲ့ PDF report ထုတ်ပေးမယ့် function
    Account ID ကို full value မပြဘဲ တစ်စိတ်တစ်ပိုင်း mask ပြထားပါတယ်
    """
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    cell_style = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, leading=10)
    header_style = ParagraphStyle("header", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.white)

    story = []

    story.append(Paragraph(title, styles["Title"]))
    story.append(
        Paragraph(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} &nbsp;|&nbsp; Total entries: {len(logs)}",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.5 * cm))

    headers = ["Time (UTC)", "Actor", "Action", "Result", "Resource Type", "Zone", "Account ID"]
    table_data = [[Paragraph(h, header_style) for h in headers]]

    for log in logs:
        row = _format_entry(log)
        table_data.append([
            Paragraph(str(row["when"]), cell_style),
            Paragraph(str(row["actor"]), cell_style),
            Paragraph(str(row["action"]), cell_style),
            Paragraph(str(row["result"]), cell_style),
            Paragraph(str(row["resource_type"]), cell_style),
            Paragraph(str(row["zone_name"]), cell_style),
            Paragraph(str(row["account_id"]), cell_style),
        ])

    col_widths = [3.2 * cm, 3.2 * cm, 4.5 * cm, 2.0 * cm, 3.0 * cm, 3.5 * cm, 3.5 * cm]
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F38020")),  # Cloudflare orange
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    story.append(table)
    doc.build(story)

    print(f"PDF report saved to {filename}")


if __name__ == "__main__":
    check_config()

    # ဥပမာ: Aug 16, 2026 (UTC) တစ်ရက်စာ audit log များကို ဆွဲမယ်
    logs = fetch_audit_logs(
        since="2026-08-16T00:00:00Z",
        before="2026-08-17T00:00:00Z",
    )

    # "လွန်ခဲ့သော N ရက်" ပုံစံ ပြန်သုံးချင်ရင် အောက်ကလိုင်းကို uncomment လုပ်ပြီး အပေါ်ကို comment ပိတ်ပါ
    # logs = fetch_audit_logs(days_back=7)

    save_to_file(logs, filename="audit_logs_2026-08-16.json")
    save_to_pdf(logs, filename="audit_report_2026-08-16.pdf")