"""
HTML report builder: Acme brand style.

Converts LLM markdown into a branded HTML email/page.
"""

import re
from datetime import date
from html import escape


def _parse_numeric(value_str: str) -> float | None:
    """Convert display strings like '$104,171.46', '9.4x', '325' to float."""
    if not value_str:
        return None
    cleaned = re.sub(r"[$,x%\s]", "", value_str)
    if cleaned.upper().endswith("K"):
        try:
            return float(cleaned[:-1]) * 1_000
        except ValueError:
            return None
    if cleaned.upper().endswith("M"):
        try:
            return float(cleaned[:-1]) * 1_000_000
        except ValueError:
            return None
    try:
        return float(cleaned)
    except ValueError:
        return None


_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: #F7F4F0;
  font-family: 'DM Sans', Arial, sans-serif;
  color: #1a1a1a;
  padding: 32px 16px;
}

.email-wrapper { max-width: 640px; margin: 0 auto; }

.header {
  background: #1C1C2E;
  border-radius: 16px 16px 0 0;
  padding: 36px 40px 32px;
}

.header-top { margin-bottom: 24px; }

.brand { font-family: 'DM Serif Display', Georgia, serif; font-size: 28px; color: #ffffff; letter-spacing: -0.5px; }
.brand span { color: #1772fd; }

.date-badge {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 100px;
  padding: 6px 14px;
  font-size: 11px;
  font-weight: 500;
  color: rgba(255,255,255,0.7);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.header-title {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  font-weight: 400;
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.body { background: #ffffff; padding: 36px 40px; }

.greeting { font-family: 'DM Serif Display', Georgia, serif; font-size: 22px; color: #1a1a1a; margin-bottom: 6px; }

.subheading { font-size: 13px; color: #888888; margin-bottom: 32px; font-weight: 400; }

.section-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #999999;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 1px solid #f0f0f0;
}

.report-section { margin-bottom: 28px; }

.body-text { font-size: 13px; color: #444444; line-height: 1.7; margin-bottom: 10px; }

.report-list { margin: 0 0 16px 0; padding-left: 20px; }

.report-list li { font-size: 13px; color: #444444; line-height: 1.7; margin-bottom: 6px; padding-left: 4px; }

.report-list li strong { color: #1a1a1a; }

code { font-family: 'Courier New', monospace; font-size: 12px; background: #f4f4f4; padding: 1px 4px; border-radius: 3px; }

.table-section { margin-bottom: 4px; overflow-x: auto; }

.product-table { width: 100%; border-collapse: collapse; }

.product-table th {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.8px;
  text-transform: uppercase;
  color: #bbbbbb;
  padding: 0 8px 10px 0;
  text-align: left;
}

.product-table th:not(:first-child) { text-align: right; }

.product-table td {
  padding: 10px 8px 10px 0;
  font-size: 13px;
  border-top: 1px solid #f4f4f4;
  vertical-align: middle;
  color: #666666;
}

.product-table td:first-child { font-weight: 500; color: #1a1a1a; }
.product-table td:not(:first-child) { text-align: right; }

.divider { height: 1px; background: #f0f0f0; margin: 24px 0; }

.footer {
  background: #FAFAF8;
  border: 1px solid #EDE9E3;
  border-top: none;
  border-radius: 0 0 16px 16px;
  padding: 24px 40px;
}

.footer-note { font-size: 11px; color: #aaaaaa; line-height: 1.6; }
.footer-note strong { color: #555555; }

.footer-badge {
  display: inline-block;
  background: #1772fd;
  color: #ffffff;
  font-size: 11px;
  font-weight: 600;
  padding: 10px 18px;
  border-radius: 100px;
  letter-spacing: 0.3px;
}
"""


def _inline(text: str) -> str:
    """Escape HTML then apply markdown and visual formatting."""
    text = escape(text)
    # Normalise triangle chars to arrow chars
    text = text.replace("▲", "↑").replace("▼", "↓")
    # Bold and code
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    # Colored arrows with percentage (e.g. ↑ 3.6% or ↓ -3.7%)
    text = re.sub(
        r"([↑▲])\s*(-?[\d,.]+\s*%?)",
        r'<span style="color:#16a34a;font-weight:600;">\1 \2</span>',
        text,
    )
    text = re.sub(
        r"([↓▼])\s*(-?[\d,.]+\s*%?)",
        r'<span style="color:#dc2626;font-weight:600;">\1 \2</span>',
        text,
    )
    # Standalone arrows with no number after (e.g. Trend column)
    text = re.sub(
        r"([↑▲])(?!\s*-?[\d,.])",
        r'<span style="color:#16a34a;font-weight:600;">\1</span>',
        text,
    )
    text = re.sub(
        r"([↓▼])(?!\s*-?[\d,.])",
        r'<span style="color:#dc2626;font-weight:600;">\1</span>',
        text,
    )
    # Sentiment badges (lookbehind avoids matching inside <strong> tags)
    text = re.sub(
        r"(?<!<)(?<!/)\bstrong\b(?!>)",
        '<span style="background:#dcfce7;color:#16a34a;font-size:10px;font-weight:700;'
        'padding:2px 7px;border-radius:100px;letter-spacing:0.5px;text-transform:uppercase;'
        'vertical-align:middle;">strong</span>',
        text,
    )
    text = re.sub(
        r"\bweak\b",
        '<span style="background:#fee2e2;color:#dc2626;font-size:10px;font-weight:700;'
        'padding:2px 7px;border-radius:100px;letter-spacing:0.5px;text-transform:uppercase;'
        'vertical-align:middle;">weak</span>',
        text,
    )
    text = re.sub(
        r"\bmoderate\b",
        '<span style="background:#fef3c7;color:#d97706;font-size:10px;font-weight:700;'
        'padding:2px 7px;border-radius:100px;letter-spacing:0.5px;text-transform:uppercase;'
        'vertical-align:middle;">moderate</span>',
        text,
    )
    text = re.sub(
        r"\bflat\b",
        '<span style="background:#fef9c3;color:#a16207;font-size:10px;font-weight:700;'
        'padding:2px 7px;border-radius:100px;letter-spacing:0.5px;text-transform:uppercase;'
        'vertical-align:middle;">flat</span>',
        text,
    )
    return text


_KPI_INVERSE = {"media spend", "discounts", "returns"}  # up is bad for these metrics

_KPI_ALLOWED = [
    "gross sales",
    "net sales",
    "total sales",
    "orders",
    "transactions",
    "media spend",
    "roi",
    "new customer orders",
    "discounts",
]


def _is_kpi_table(header_cells: list[str]) -> bool:
    headers = [h.lower().strip() for h in header_cells]
    return "metric" in headers and "value" in headers


def _filter_kpi_rows(body_rows: list[list[str]]) -> list[list[str]]:
    """Keep only the allowed KPI rows, in the defined order."""
    by_name = {r[0].strip().lower(): r for r in body_rows if r}
    return [by_name[name] for name in _KPI_ALLOWED if name in by_name]


def _build_kpi_cards_html(body_rows: list[list[str]]) -> str:
    """Render KPI table rows as a 4-per-row card grid (email-table-based layout)."""
    cards = []
    for i, row in enumerate(body_rows):
        metric    = row[0].strip() if len(row) > 0 else ""
        value     = row[1].strip() if len(row) > 1 else ""
        delta_raw = row[2].strip() if len(row) > 2 else ""
        trend_raw = row[3].strip() if len(row) > 3 else ""

        # Detect direction from raw delta before any processing
        delta_norm = delta_raw.replace("▲", "↑").replace("▼", "↓")
        is_up   = "↑" in delta_norm
        is_down = "↓" in delta_norm

        # Extract sentiment word for badge
        sentiment_match = re.search(r"\b(strong|weak|moderate|flat)\b", trend_raw, re.IGNORECASE)
        sentiment = sentiment_match.group(0).lower() if sentiment_match else ""
        trend_html = _inline(sentiment) if sentiment else ""

        if i == 0:
            # First card — Acme blue highlight
            card_bg, card_border = "#1772fd", "#1772fd"
            label_col, value_col = "rgba(255,255,255,0.7)", "#ffffff"
            delta_html = (
                f'<div style="font-size:11px;font-weight:600;color:rgba(255,255,255,0.9);margin-bottom:4px;">'
                f'{escape(delta_norm)}</div>'
            )
            trend_html = (
                f'<div style="font-size:10px;color:rgba(255,255,255,0.6);">{sentiment.upper()}</div>'
                if sentiment else ""
            )
        else:
            card_bg, card_border = "#FAFAF8", "#EDE9E3"
            label_col, value_col = "#999999", "#1a1a1a"
            inverse = metric.lower() in _KPI_INVERSE
            accent = (
                ("#dc2626" if is_up else "#16a34a") if inverse
                else ("#16a34a" if is_up else ("#dc2626" if is_down else "#999999"))
            )
            delta_html = (
                f'<div style="font-size:11px;font-weight:600;color:{accent};margin-bottom:4px;">'
                f'{escape(delta_norm)}</div>'
            )
            trend_html = f'<div style="margin-top:2px;">{trend_html}</div>' if trend_html else ""

        cards.append(
            f'<td data-kpi-metric="{escape(metric)}" data-kpi-value="{escape(value)}"'
            f' style="width:25%;padding:0 6px 8px 0;vertical-align:top;">'
            f'<div style="background:{card_bg};border:1px solid {card_border};border-radius:12px;padding:16px;">'
            f'<div style="font-size:10px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;'
            f'color:{label_col};margin-bottom:6px;">{escape(metric)}</div>'
            f'<div style="font-family:\'DM Serif Display\',Georgia,serif;font-size:20px;'
            f'color:{value_col};line-height:1;margin-bottom:6px;">{escape(value)}</div>'
            f'{delta_html}{trend_html}'
            f'</div></td>'
        )

    rows_html = []
    for j in range(0, len(cards), 4):
        group = cards[j:j+4]
        while len(group) < 4:
            group.append('<td style="width:25%;padding:0;"></td>')
        rows_html.append(f'<tr>{"".join(group)}</tr>')

    return (
        '<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;">'
        + "".join(rows_html)
        + "</table>"
    )


def _build_table_html(table_lines: list[str]) -> str:
    header_cells: list[str] | None = None
    body_rows: list[list[str]] = []
    in_header = True

    for line in table_lines:
        if re.match(r"^\|[\s\-:]+\|", line):
            in_header = False
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if in_header:
            header_cells = cells
            in_header = False
        else:
            body_rows.append(cells)

    if not header_cells and not body_rows:
        return ""

    if header_cells and _is_kpi_table(header_cells) and body_rows:
        return _build_kpi_cards_html(_filter_kpi_rows(body_rows))

    parts = ['<div class="table-section"><table class="product-table">']
    if header_cells:
        parts.append("<thead><tr>")
        for cell in header_cells:
            parts.append(f"<th>{escape(cell)}</th>")
        parts.append("</tr></thead>")
    if body_rows:
        parts.append("<tbody>")
        for row in body_rows:
            processed = [_inline(cell) for cell in row]
            row_text = " ".join(processed)
            is_up = "color:#16a34a" in row_text
            is_down = "color:#dc2626" in row_text
            parts.append("<tr>")
            for i, cell in enumerate(processed):
                if i == 1 and len(processed) >= 3 and (is_up or is_down):
                    bg = "#dcfce7" if is_up else "#fee2e2"
                    color = "#16a34a" if is_up else "#dc2626"
                    cell = (
                        f'<span style="background:{bg};color:{color};padding:3px 8px;'
                        f'border-radius:6px;display:inline-block;font-weight:600;">{cell}</span>'
                    )
                parts.append(f"<td>{cell}</td>")
            parts.append("</tr>")
        parts.append("</tbody>")
    parts.append("</table></div>")
    return "".join(parts)


_CHART_METRICS = ["Gross Sales", "Total Sales", "Orders", "ROI"]
_CHART_HEIGHT_PX = 48
_CHART_BAR_COLORS = {
    "Gross Sales": "#1772fd",
    "Total Sales": "#1772fd",
    "Orders":      "#6366f1",
    "ROI":         "#16a34a",
}


def _build_trend_chart_html(history: list[dict]) -> str:
    """
    Plots trend chart for _CHART_METRICS over the given history.
    """
    if len(history) < 2:
        return ""

    # Show last 5 days
    days = history[-5:]
    dates = [d["date"][-5:] for d in days]  # MM-DD

    rows_html = []
    for metric in _CHART_METRICS:
        raw_vals = [_parse_numeric(d["metrics"].get(metric, "")) for d in days]
        valid = [(i, v) for i, v in enumerate(raw_vals) if v is not None]
        if not valid:
            continue

        max_v = max(v for _, v in valid)
        min_v = min(v for _, v in valid)
        span = max_v - min_v or 1
        color = _CHART_BAR_COLORS.get(metric, "#1772fd")

        bars = []
        for i, date_label in enumerate(dates):
            val = raw_vals[i]
            if val is None:
                bars.append(
                    f'<td style="width:36px;padding:0 2px;vertical-align:bottom;">'
                    f'<div style="height:{_CHART_HEIGHT_PX}px;width:100%;"></div></td>'
                )
                continue
            bar_h = max(4, int(((val - min_v) / span) * _CHART_HEIGHT_PX))
            day_val = days[i]["metrics"].get(metric, "")
            bars.append(
                f'<td style="width:36px;padding:0 2px;vertical-align:bottom;" title="{date_label}: {day_val}">'
                f'<div style="height:{bar_h}px;width:100%;background:{color};border-radius:3px 3px 0 0;"></div></td>'
            )

        # Date label row (show first, middle, last)
        label_cells = []
        show_indices = {0, len(dates) // 2, len(dates) - 1}
        for i, date_label in enumerate(dates):
            txt = date_label if i in show_indices else ""
            label_cells.append(
                f'<td style="width:20px;font-size:8px;color:#bbbbbb;text-align:center;padding-top:2px;">{txt}</td>'
            )

        rows_html.append(
            f'<tr>'
            f'<td style="font-size:9px;font-weight:600;letter-spacing:0.5px;text-transform:uppercase;'
            f'color:#999999;white-space:nowrap;padding-right:10px;vertical-align:bottom;'
            f'padding-bottom:0;">{escape(metric)}</td>'
            f'<td><table cellpadding="0" cellspacing="0" border="0" style="height:{_CHART_HEIGHT_PX}px;">'
            f'<tr>{"".join(bars)}</tr>'
            f'<tr>{"".join(label_cells)}</tr>'
            f'</table></td>'
            f'</tr>'
            f'<tr><td colspan="2" style="height:10px;"></td></tr>'
        )

    if not rows_html:
        return ""

    return (
        '<div class="report-section">'
        '<div class="section-label">Performance Trend</div>'
        '<table cellpadding="0" cellspacing="0" border="0" width="100%">'
        + "".join(rows_html)
        + "</table></div>"
    )


def _parse_markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    sections: list[str] = []
    current_header: str | None = None
    current_content: list[str] = []

    def flush() -> None:
        if current_header is not None or current_content:
            header_html = (
                f'<div class="section-label">{escape(current_header)}</div>'
                if current_header else ""
            )
            sections.append(
                f'<div class="report-section">{header_html}{"".join(current_content)}</div>'
            )

    i = 0
    while i < len(lines):
        line = lines[i]

        if line.startswith("### ") or line.startswith("## "):
            flush()
            current_header = line.lstrip("#").strip()
            current_content = []
            i += 1
            continue

        # Numbered sections: "1. Title", "2. Title" etc.
        if re.match(r"^\d+\.\s+\S", line):
            flush()
            current_header = re.sub(r"^\d+\.\s+", "", line).strip()
            current_content = []
            i += 1
            continue

        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            current_content.append(_build_table_html(table_lines))
            continue

        if re.match(r"^\s*[\*\-]\s+", line):
            items = []
            while i < len(lines) and re.match(r"^\s*[\*\-]\s+", lines[i]):
                text = re.sub(r"^\s*[\*\-]\s+", "", lines[i])
                items.append(f"<li>{_inline(text)}</li>")
                i += 1
            current_content.append(f'<ul class="report-list">{"".join(items)}</ul>')
            continue

        if line.strip():
            current_content.append(f'<p class="body-text">{_inline(line.strip())}</p>')

        i += 1

    flush()
    return "\n".join(sections)


def build_html(
    client_name: str,
    report_markdown: str,
    report_date: date | None = None,
    brand_name: str | None = None,
    kpi_history: list[dict] | None = None,
    dashboard_url: str | None = None,
) -> str:
    """
    Convert the LLM markdown report into a branded HTML page and return it as a string.

    Args:
        client_name: Shown in the subheading and title.
        report_markdown: Markdown text from llm_client.analyse().
        report_date: Date in the header. Defaults to today.
        brand_name: Short name shown in the header (e.g. "Client B"). Defaults to client_name.
        kpi_history: Historical KPI data from history_manager.get_kpi_history().
        dashboard_url: URL for the "View Dashboard" footer button.

    Returns:
        HTML string ready to send as email body or upload to GCS.
    """
    if report_date is None:
        report_date = date.today()

    date_str = report_date.strftime("%d %b %Y")
    client_escaped = escape(client_name)
    brand_escaped = escape(brand_name or client_name)
    body_content = _parse_markdown_to_html(report_markdown)
    trend_chart = _build_trend_chart_html(kpi_history or [])
    dashboard_btn = (
        f'<a href="{escape(dashboard_url)}" target="_blank" style="display:inline-block;'
        f'background:#1772fd;color:#ffffff;font-size:11px;font-weight:600;'
        f'padding:10px 18px;border-radius:100px;letter-spacing:0.3px;'
        f'text-decoration:none;">View Dashboard</a>'
        if dashboard_url else
        '<span class="footer-badge">Acme Intelligence</span>'
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{client_escaped} — Acme AI Insights</title>
<style>{_CSS}</style>
</head>
<body>
<div class="email-wrapper">

  <div class="header">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td><span class="brand">{brand_escaped}<span>.</span></span></td>
        <td align="right"><span class="date-badge">{date_str} · AI Insights</span></td>
      </tr>
    </table>
    <div class="header-title" style="margin-top:24px;">Acme AI Insights — Daily Performance</div>
  </div>

  <div class="body">
    <div class="greeting">{client_escaped}</div>
    <div class="subheading">Acme AI Insights · {date_str}</div>

    {body_content}

    {trend_chart}

    <div class="divider"></div>
    <div style="font-size:12px;color:#aaa;line-height:1.7;">
      This report is generated automatically by Acme&#39;s marketing intelligence pipeline.
      Data reflects <strong style="color:#555">yesterday&#39;s performance</strong> compared to the previous day.
    </div>
  </div>

  <div class="footer">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr>
        <td><div class="footer-note"><strong>Powered by Acme</strong><br>Marketing Intelligence Platform</div></td>
        <td align="right">{dashboard_btn}</td>
      </tr>
    </table>
  </div>

</div>
</body>
</html>"""
