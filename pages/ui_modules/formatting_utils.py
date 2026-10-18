"""
pages/ui_modules/formatting_utils.py

Number formatting and utility functions for the Working Capital dashboard.
Extracted from pages/_ui.py for better modularity.
"""

import math
from typing import List
import pandas as pd


def _is_missing(value) -> bool:
    """Check if a value is missing (None or NaN)."""
    try:
        return value is None or (isinstance(value, float) and math.isnan(value))
    except TypeError:
        return False


def fmt_money(value) -> str:
    """Compact currency-like formatting: $84B / $2M / $950K / $— (no decimals)."""
    if _is_missing(value):
        return "$—"
    sign = "-" if value < 0 else ""
    v = abs(float(value))
    if v >= 1e9:
        return f"{sign}${v / 1e9:,.0f}B"
    if v >= 1e6:
        return f"{sign}${v / 1e6:,.0f}M"
    if v >= 1e3:
        return f"{sign}${v / 1e3:,.0f}K"
    return f"{sign}${v:,.0f}"


def fmt_money_full(value) -> str:
    """Full precision for table cells: $84,284,000,000."""
    if _is_missing(value):
        return "—"
    return f"${float(value):,.0f}"


def fmt_days(value) -> str:
    """Format days value with 'd' suffix."""
    if _is_missing(value):
        return "—"
    return f"{float(value):,.0f} d"


def fmt_pct(value, decimals: int = 1) -> str:
    """Format percentage value."""
    if _is_missing(value):
        return "—"
    return f"{float(value):.{decimals}%}"


def fmt_pp(value, decimals: int = 0) -> str:
    """Format percentage-point delta, e.g. +10pp / -5pp."""
    if _is_missing(value):
        return "—"
    return f"{float(value) * 100:+.{decimals}f}pp"


def fmt_ratio(value) -> str:
    """Format ratio value with '×' suffix."""
    if _is_missing(value):
        return "—"
    return f"{float(value):,.2f}×"


def fmt_year(value) -> str:
    """Format year value."""
    if _is_missing(value):
        return "—"
    return str(int(value))


def year_labels(df: pd.DataFrame) -> List[str]:
    """Extract formatted year labels from a DataFrame with fiscal_year column."""
    if df.empty or "fiscal_year" not in df.columns:
        return []
    return [fmt_year(year) for year in df["fiscal_year"]]