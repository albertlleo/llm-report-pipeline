"""
Local preview — tests the Trends agent with fake historical data.
Usage: uv run python tests/preview_trends.py

Requires GCP credentials:
  gcloud auth application-default login
"""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import llm_client

CLIENT_ID   = "client-b-demo"
CLIENT_NAME = "Client B (Test)"

SAMPLE_HISTORY = [
    {
        "date": (date.today() - timedelta(days=i)).isoformat(),
        "metrics": {
            "Gross Sales":         f"${104_000 + i * 1_500 - i * i * 80:,.2f}",
            "Net Sales":           f"${90_000  + i * 1_200 - i * i * 60:,.2f}",
            "Total Sales":         f"${94_000  + i * 1_300 - i * i * 70:,.2f}",
            "Orders":              str(320 + i * 3 - i),
            "Media Spend":         f"${10_000  + i * 200:,.2f}",
            "ROI":                 f"{9.4 + i * 0.15:.1f}x",
            "New Customer Orders": str(318 + i * 3 - i),
            "Discounts":           f"${11_500  + i * 100:,.2f}",
        },
    }
    for i in range(10, 0, -1)  # 10 days ago → yesterday
]

SAMPLE_TODAY_REPORT = """
2. KPI summary
| Metric | Value | Δ% vs yesterday | Trend |
|--------|-------|-----------------|-------|
| Gross Sales | $104,171.46 | ↓ 3.7% | ↓ weak |
| Total Sales | $94,766.08 | ↓ 4.0% | ↓ weak |
| Orders | 325 | ↓ 0.3% | — flat |
| Media Spend | $10,132.74 | ↓ 19.8% | ↓ weak |
| ROI | 10.3x | ↑ 20.1% | ↑ strong |
"""

print(f"Running Trends agent with {len(SAMPLE_HISTORY)} days of history...\n")

result = llm_client.analyse_trends(CLIENT_ID, CLIENT_NAME, SAMPLE_HISTORY, SAMPLE_TODAY_REPORT)

if result:
    print("=== Section 7. Trends ===\n")
    print(result)
else:
    print("No trends generated (need at least 2 days of history).")
