"""
Pre-aggregates raw BigQuery DataFrames before sending to the LLM to avoid token cap.

Groups numeric columns by date, finds the best comparison period
(yesterday first, then same weekday last week), and computes Δ% for
every numeric column. Reduces to 2 rows.
Tables without a date column are passed through unchanged.
"""

import logging
from datetime import date, timedelta

import pandas as pd

log = logging.getLogger(__name__)


def aggregate_tables(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Aggregate all tables. Returns a new dict with the same keys."""
    return {name: _aggregate(name, df) for name, df in tables.items()}


def _aggregate(table_name: str, df: pd.DataFrame) -> pd.DataFrame:
    if "date" not in df.columns or df.empty:
        log.info("Aggregator %s : no date column, passing through (%d rows)", table_name, len(df))
        return df

    # Removing rows with future dates, and saving complete days
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date  # Format date
    df = df[df["date"] < date.today()]  # If any row with date greater than today, we skip it
    if df.empty:
        log.warning("Aggregator %s : no complete days available, skipping", table_name)
        return df
    numeric_cols = df.select_dtypes(
        include="number").columns.tolist()  # We keep only numeric cols, not text like period

    if not numeric_cols:
        log.info("Aggregator %s : no numeric columns, passing through", table_name)
        return df

    # Group all lines for the same day, and we sum them up.
    # Eg: 613 rows with orders =1 for 13-may -> 1 row with orders=639
    daily = (
        df.groupby("date")[numeric_cols]
        .sum()
        .reset_index()
        .sort_values("date", ascending=False)  # Most recent day first
        .reset_index(drop=True)
    )

    if len(daily) < 2:
        log.info("Aggregator: %s — only %d date(s), passing through", table_name, len(daily))
        return daily

    # today is the most recent complete day (last day with complete data)
    today = daily.iloc[0]
    today_date = today["date"]

    # Searching the best result to compare for the last period.
    # We try yesterday first, if there is none, we try same day from last week (7 day offset).
    comparison, comparison_label = _find_comparison(daily, today_date)

    today_dict: dict = {"period": "today", "date": str(today_date)}
    comp_dict: dict = {"period": comparison_label, "date": str(comparison["date"])}

    # Compute Delta
    for col in numeric_cols:
        today_dict[col] = today[col]
        comp_dict[col] = comparison[col]
        comp_val = comparison[col]
        if comp_val and comp_val != 0:
            today_dict[f"{col}_Δ%"] = round((today[col] - comp_val) / abs(comp_val) * 100, 1)

    result = pd.DataFrame([today_dict, comp_dict])
    log.info(
        "Aggregator: %s — %d raw rows → 2 aggregated rows (today=%s vs %s=%s)",
        table_name, len(df), today_date, comparison_label, comparison["date"],
    )
    return result


def _find_comparison(daily: pd.DataFrame, today_date) -> tuple:
    for offset, label in [(1, "yesterday"), (7, "last_week_same_day")]:
        target = today_date - timedelta(days=offset)
        match = daily[daily["date"] == target]
        if not match.empty:
            return match.iloc[0], label
    fallback = daily.iloc[1]
    log.warning("Aggregator: no yesterday/last-week found — using %s as comparison", fallback["date"])
    return fallback, str(fallback["date"])
