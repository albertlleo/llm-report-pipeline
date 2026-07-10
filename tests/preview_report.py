"""
Local preview script — generates a sample HTML report and opens it in the browser.
Usage: uv run python tests/preview_report.py
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.report_builder import build_html

SAMPLE_MARKDOWN = """
1. Headline
Soft day — total sales are down 4.0% versus yesterday while order volume held nearly flat.

2. KPI summary
| Metric | Value | Δ% vs yesterday | Trend |
|--------|-------|-----------------|-------|
| Gross Sales | $104,171.46 | ↓ 3.7% | ↓ weak |
| Net Sales | $90,920.08 | ↓ 3.1% | ↓ weak |
| Total Sales | $94,766.08 | ↓ 4.0% | ↓ weak |
| Orders | 325 | ↓ 0.3% | — flat |
| Media Spend | $10,132.74 | ↓ 12.1% | ↓ weak |
| ROI | 9.4x | ↑ 8.2% | ↑ strong |
| New Customer Orders | 323 | ↓ 0.3% | — flat |
| Discounts | $11,847.78 | ↑ 2.1% | ↑ moderate |

3. Media spend
Total Spend: $10,132.74
Top 3 channels: Advertorial ($5,030.00), Performance Max ($2,032.51), and TV - Regional ($831.74).

- Advertorial: $5,030.00
- Performance Max: $2,032.51
- TV - Regional: $831.74
- Shopping: $573.97
- StackAdapt - CTV: $539.12
- Bing: $294.65
- StackAdapt - Display: $192.61
- StackAdapt - Native: $143.15
- Search: $126.17
- TV - Metro: $120.00
- Demand Gen: $91.04
- TikTok: $69.47
- StackAdapt - Video: $63.23
- Meta: $25.08

4. New Users
New Customer Orders: 323 (↓ 0.3% vs yesterday)

5. Expenses
- Discounts: $11,847.78
- Returns: $1,403.60
- Shipping: $133.94
- Tax: $3,712.06

6. Watch-outs
- Sales values (Total/Gross/Net) are trending down between 3.1% and 4.0% despite order volume remaining nearly flat at ↓ 0.3%.
- Shipping revenue saw a significant decline of ↓ 43.2% compared to yesterday.
- Tax amounts dropped ↓ 20.6% versus yesterday, diverging from the more moderate ↓ 4.0% drop in total sales.
"""

SAMPLE_HISTORY = [
    {
        "date": (date.today() - timedelta(days=i)).isoformat(),
        "metrics": {
            "Gross Sales": f"${104_000 + i * 1_500 - i * i * 80:,.2f}",
            "Net Sales":   f"${90_000 + i * 1_200 - i * i * 60:,.2f}",
            "Total Sales": f"${94_000 + i * 1_300 - i * i * 70:,.2f}",
            "Orders":      str(320 + i * 3 - i),
            "Media Spend": f"${10_000 + i * 200:,.2f}",
            "ROI":         f"{9.4 + i * 0.15:.1f}x",
            "New Customer Orders": str(318 + i * 3 - i),
            "Discounts":   f"${11_500 + i * 100:,.2f}",
        },
    }
    for i in range(14, 0, -1)  # 14 days ago → yesterday
]

OUTPUT_PATH = "/tmp/acme_preview_report.html"

html = build_html(
    "Client B (Test)", SAMPLE_MARKDOWN, date.today(),
    brand_name="Client B", kpi_history=SAMPLE_HISTORY,
)

with open(OUTPUT_PATH, "w") as f:
    f.write(html)

print(f"Report saved → {OUTPUT_PATH}")
subprocess.run(["open", OUTPUT_PATH])
