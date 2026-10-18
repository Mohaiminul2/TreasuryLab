"""
finance_logic.py

Core financial calculations layer. Takes the normalized long-format data
produced by data_fetcher.py and computes:
    - Working capital metrics: DSO, DPO, DIO, Cash Conversion Cycle (CCC)
    - Liquidity ratios: Current Ratio, Quick Ratio
    - Working Capital Requirement (WCR)
    - Data-quality validation checks

This module is framework-agnostic — it doesn't know about Dash. It just
takes/returns pandas DataFrames so it can be unit tested independently
and reused if the dashboard framework ever changes.

Usage:
    from finance_logic import build_metrics_table
    metrics_df = build_metrics_table("data/processed/financials.csv")
"""

import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd

from config import VALIDATION_THRESHOLDS, DAYS_IN_YEAR

logger = logging.getLogger(__name__)


def load_financials(path: str = "data/processed/financials.csv") -> pd.DataFrame:
    """Load the long-format financials produced by data_fetcher.py."""
    df = pd.read_csv(path)
    return df


def pivot_to_wide(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot long-format (ticker, statement, fiscal_year, field, value) into
    wide format: one row per (ticker, fiscal_year), one column per field.
    This is the shape most convenient for ratio calculations.

    If the same (ticker, fiscal_year, field) appears more than once
    (multiple raw yfinance labels mapped to one standard field), the
    first non-null value wins — pivot_table's aggfunc="first" would
    instead keep whichever duplicate row landed first, even a NaN.
    """
    deduped = (
        df.dropna(subset=["value"])
        .drop_duplicates(subset=["ticker", "fiscal_year", "field"], keep="first")
    )
    all_keys = df[["ticker", "fiscal_year", "field"]].drop_duplicates()
    deduped = (
        all_keys.merge(deduped, on=["ticker", "fiscal_year", "field"], how="left")
        .drop(columns=["statement"], errors="ignore")
    )
    wide = deduped.pivot_table(
        index=["ticker", "fiscal_year"],
        columns="field",
        values="value",
        aggfunc="first",
    ).reset_index()
    wide.columns.name = None
    return wide


def safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Divide two series, returning NaN (not error) on zero/missing denominator."""
    with np.errstate(divide="ignore", invalid="ignore"):
        result = numerator / denominator
    result = result.replace([np.inf, -np.inf], np.nan)
    return result


def compute_working_capital_metrics(wide_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute DSO, DPO, DIO, CCC, liquidity ratios, and Working Capital
    Requirement for each (ticker, fiscal_year) row.

    Required input columns (missing ones produce NaN output, not errors):
        revenue, cogs, accounts_receivable, accounts_payable, inventory,
        current_assets, current_liabilities, cash
    """
    df = wide_df.copy()

    required_cols = [
        "revenue", "cogs", "accounts_receivable", "accounts_payable",
        "inventory", "current_assets", "current_liabilities", "cash",
    ]
    for col in required_cols:
        if col not in df.columns:
            logger.warning(
                "Column '%s' missing entirely from input data — related "
                "metrics will be NaN for all rows.", col
            )
            df[col] = np.nan

    # Sort so that shift(-1) style period-over-period logic works predictably
    df = df.sort_values(["ticker", "fiscal_year"]).reset_index(drop=True)

    # --- Working capital cycle metrics ---
    df["dso"] = safe_divide(df["accounts_receivable"], df["revenue"]) * DAYS_IN_YEAR
    df["dpo"] = safe_divide(df["accounts_payable"], df["cogs"]) * DAYS_IN_YEAR
    df["dio"] = safe_divide(df["inventory"], df["cogs"]) * DAYS_IN_YEAR
    df["ccc"] = df["dso"] + df["dio"] - df["dpo"]

    # --- Liquidity ratios ---
    df["current_ratio"] = safe_divide(df["current_assets"], df["current_liabilities"])
    quick_assets = df["current_assets"] - df["inventory"]
    df["quick_ratio"] = safe_divide(quick_assets, df["current_liabilities"])

    # --- Working Capital Requirement ---
    # WCR = (AR + Inventory - AP), the net operating cash tied up in the
    # working capital cycle. Positive = cash tied up; negative = cash freed.
    df["working_capital_requirement"] = (
        df["accounts_receivable"] + df["inventory"] - df["accounts_payable"]
    )

    # --- Year-over-year growth (useful for forecasting baseline) ---
    df["revenue_growth"] = df.groupby("ticker")["revenue"].pct_change()

    return df


def validate_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run sanity checks and return a validation report DataFrame flagging
    rows with implausible values. This does NOT modify the input data —
    it's meant to surface extraction/data-quality issues for manual review.
    """
    issues = []

    for _, row in df.iterrows():
        ticker, year = row["ticker"], row["fiscal_year"]

        # Balance sheet identity sanity check (loose tolerance since we
        # don't have full liabilities/equity breakdown from yfinance by default)
        if pd.notna(row.get("current_assets")) and pd.notna(row.get("current_liabilities")):
            if row["current_assets"] < 0 or row["current_liabilities"] < 0:
                issues.append((ticker, year, "Negative current assets/liabilities"))

        # Revenue growth sanity bound
        if pd.notna(row.get("revenue_growth")):
            if abs(row["revenue_growth"]) > VALIDATION_THRESHOLDS["max_revenue_growth"]:
                issues.append((ticker, year, f"Implausible revenue growth: {row['revenue_growth']:.1%}"))

        # Negative inventory/AR/AP (shouldn't happen on real filings)
        for field in ["accounts_receivable", "accounts_payable", "inventory"]:
            val = row.get(field)
            if pd.notna(val) and val < 0:
                issues.append((ticker, year, f"Negative {field}: {val}"))

        # CCC sanity bound (extreme values usually indicate a data issue)
        if pd.notna(row.get("ccc")) and abs(row["ccc"]) > VALIDATION_THRESHOLDS["max_ccc_days"]:
            issues.append((ticker, year, f"CCC out of plausible range: {row['ccc']:.0f} days"))

    report = pd.DataFrame(issues, columns=["ticker", "fiscal_year", "issue"])
    if not report.empty:
        logger.warning("Validation found %d potential data issues.", len(report))
    else:
        logger.info("Validation passed with no flagged issues.")

    return report


def build_metrics_table(
    financials_path: str = "data/processed/financials.csv",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    End-to-end: load raw financials, pivot, compute metrics, validate.
    Returns (metrics_df, validation_report_df).
    """
    raw = load_financials(financials_path)
    wide = pivot_to_wide(raw)
    metrics = compute_working_capital_metrics(wide)
    validation_report = validate_metrics(metrics)
    return metrics, validation_report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    metrics_df, report_df = build_metrics_table()

    out_path = Path("data/processed/metrics.csv")
    metrics_df.to_csv(out_path, index=False)
    logger.info("Metrics saved to %s (%d rows)", out_path, len(metrics_df))

    if not report_df.empty:
        report_path = Path("data/processed/validation_report.csv")
        report_df.to_csv(report_path, index=False)
        logger.info("Validation report saved to %s (%d issues)", report_path, len(report_df))