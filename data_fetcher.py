"""
data_fetcher.py

Pulls annual Income Statement, Balance Sheet, and Cash Flow Statement
data from yfinance for a configurable list of tickers, normalizes the
field names into a standard schema, and caches results locally so the
Dash app never needs to hit yfinance live at runtime.

Usage:
    python data_fetcher.py            # fetches all DEFAULT_TICKERS (merges with existing)
    python data_fetcher.py PG NKE     # fetches specific tickers (merges with existing)
    python data_fetcher.py --replace PG NKE  # full overwrite, only these tickers

Output:
    data/raw_cache/{TICKER}_{statement}.csv   (raw yfinance dumps, for debugging)
    data/processed/financials.csv             (long-format, normalized, all tickers combined)
"""

import logging
import sys
from pathlib import Path
from typing import List

import pandas as pd
import yfinance as yf

from config import DEFAULT_TICKERS as _CONFIG_TICKERS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_TICKERS: List[str] = list(_CONFIG_TICKERS)

RAW_CACHE_DIR = Path("data/raw_cache")
PROCESSED_DIR = Path("data/processed")
RAW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# Field name mapping: yfinance's row labels are inconsistent across tickers
# and change occasionally between yfinance versions. We map every known
# variant to a single standard field name.
#
# PRIORITY: when multiple raw labels map to the same standard field
# (e.g. "Accounts Payable" and "Payables And Accrued Expenses"), the
# FIRST entry in this list wins — later aliases are only used when the
# preferred label is absent. Order therefore encodes precedence:
#   - Accounts Payable (trade payables) over Payables+Accrued (DPO/DIO
#     must use trade AP, not accrued expenses)
#   - Net Income (total, incl. minority interest) over Common-Stockholders-only
#   - Cash And Cash Equivalents over the +Short-Term-Investments variant
# If a ticker uses a label not in this list, it shows up as
# "UNMAPPED: <label>" in the warning log so you can extend this dict.
# --------------------------------------------------------------------------

BALANCE_SHEET_MAP = {
    "Accounts Receivable": "accounts_receivable",
    "Net Receivables": "accounts_receivable",
    "Receivables": "accounts_receivable",
    "Accounts Payable": "accounts_payable",
    "Payables And Accrued Expenses": "accounts_payable",
    "Inventory": "inventory",
    "Cash And Cash Equivalents": "cash",
    "Cash Cash Equivalents And Short Term Investments": "cash",
    "Current Assets": "current_assets",
    "Current Liabilities": "current_liabilities",
    "Total Assets": "total_assets",
    "Total Liabilities Net Minority Interest": "total_liabilities",
    "Stockholders Equity": "total_equity",
}

INCOME_STMT_MAP = {
    "Total Revenue": "revenue",
    "Operating Revenue": "revenue",
    "Cost Of Revenue": "cogs",
    "Reconciled Cost Of Revenue": "cogs",
    "Gross Profit": "gross_profit",
    "Operating Expense": "operating_expense",
    "Operating Income": "operating_income",
    "Net Income": "net_income",
    "Net Income Common Stockholders": "net_income",
}

CASHFLOW_MAP = {
    "Operating Cash Flow": "operating_cf",
    "Cash Flow From Continuing Operating Activities": "operating_cf",
    "Investing Cash Flow": "investing_cf",
    "Cash Flow From Continuing Investing Activities": "investing_cf",
    "Financing Cash Flow": "financing_cf",
    "Cash Flow From Continuing Financing Activities": "financing_cf",
    "Free Cash Flow": "free_cash_flow",
    "Capital Expenditure": "capex",
    "Depreciation And Amortization": "depreciation_amortization",
}

STATEMENT_CONFIGS = [
    ("balance_sheet", "balance_sheet", BALANCE_SHEET_MAP),
    ("income_stmt", "income_stmt", INCOME_STMT_MAP),
    ("cashflow", "cashflow", CASHFLOW_MAP),
]


def fetch_raw_statement(ticker_obj: yf.Ticker, attr_name: str) -> pd.DataFrame:
    """Fetch a single annual statement (balance_sheet / income_stmt / cashflow)."""
    df = getattr(ticker_obj, attr_name)
    if df is None or df.empty:
        return pd.DataFrame()
    return df


def normalize_statement(
    df: pd.DataFrame, field_map: dict, ticker: str, statement_name: str
) -> pd.DataFrame:
    """
    Convert a wide yfinance statement (rows=line items, cols=fiscal years)
    into a long-format DataFrame with standardized field names.

    When several raw labels map to the same standard field (e.g. "Accounts
    Payable" and "Payables And Accrued Expenses"), the earlier entry in
    field_map wins; later aliases are used only for years where the
    preferred label has no value. Logs any row labels not found in
    field_map so the mapping dict can be extended over time.
    """
    if df.empty:
        return pd.DataFrame()

    # Reverse field_map: standard_field -> raw labels in priority order
    # (dict insertion order). The first label that has a value for a given
    # fiscal year wins, so a precise label like "Accounts Payable"
    # (trade payables) always beats the looser "Payables And Accrued
    # Expenses" alias when both are present.
    labels_by_field: dict = {}
    for raw_label, standard_field in field_map.items():
        labels_by_field.setdefault(standard_field, []).append(raw_label)

    records = []
    unmapped = set()
    mapped_labels = set()

    for standard_field, candidate_labels in labels_by_field.items():
        available = [lbl for lbl in candidate_labels if lbl in df.index]
        mapped_labels.update(available)
        if not available:
            continue
        for period in df.columns:
            value = None
            for lbl in available:  # priority order
                if lbl in df.index and pd.notna(df.loc[lbl, period]):
                    value = df.loc[lbl, period]
                    break
            records.append(
                {
                    "ticker": ticker,
                    "statement": statement_name,
                    "fiscal_year": pd.to_datetime(period).year,
                    "field": standard_field,
                    "value": value,
                }
            )

    unmapped = {lbl for lbl in df.index if lbl not in mapped_labels}

    if unmapped:
        logger.warning(
            "[%s/%s] %d unmapped row label(s) skipped: %s",
            ticker,
            statement_name,
            len(unmapped),
            sorted(unmapped),
        )

    return pd.DataFrame(records)


def fetch_ticker(ticker: str) -> pd.DataFrame:
    """Fetch and normalize all three statements for a single ticker."""
    logger.info("Fetching %s ...", ticker)
    t = yf.Ticker(ticker)

    all_records = []
    any_data_found = False

    for attr_name, statement_label, field_map in STATEMENT_CONFIGS:
        raw_df = fetch_raw_statement(t, attr_name)

        # Save raw dump for debugging / manual inspection
        raw_path = RAW_CACHE_DIR / f"{ticker}_{statement_label}.csv"
        if not raw_df.empty:
            raw_df.to_csv(raw_path)
            any_data_found = True
        else:
            logger.warning(
                "[%s] %s returned EMPTY. This ticker may have incomplete "
                "yfinance coverage — consider swapping it out.",
                ticker,
                statement_label,
            )

        normalized = normalize_statement(raw_df, field_map, ticker, statement_label)
        if not normalized.empty:
            all_records.append(normalized)

    if not any_data_found:
        logger.error(
            "[%s] NO DATA returned for any statement. Skipping this ticker "
            "entirely. Try a different, more liquid/large-cap ticker.",
            ticker,
        )
        return pd.DataFrame()

    return pd.concat(all_records, ignore_index=True) if all_records else pd.DataFrame()


def fetch_all(tickers: List[str]) -> pd.DataFrame:
    """Fetch and combine normalized data for a list of tickers."""
    all_data = []
    failed_tickers = []

    for ticker in tickers:
        try:
            df = fetch_ticker(ticker)
            if df.empty:
                failed_tickers.append(ticker)
            else:
                all_data.append(df)
        except Exception as e:
            logger.error("[%s] Fetch failed with error: %s", ticker, e)
            failed_tickers.append(ticker)

    if failed_tickers:
        logger.warning(
            "The following tickers returned no usable data and were "
            "excluded: %s. Replace them with alternative large-cap tickers "
            "in DEFAULT_TICKERS.",
            failed_tickers,
        )

    if not all_data:
        raise RuntimeError(
            "No data was successfully fetched for ANY ticker. Check your "
            "internet connection and yfinance installation "
            "(pip install --upgrade yfinance)."
        )

    combined = pd.concat(all_data, ignore_index=True)
    return combined


def _load_existing_financials() -> pd.DataFrame:
    """Load existing financials.csv if present, return empty DataFrame otherwise."""
    output_path = PROCESSED_DIR / "financials.csv"
    if output_path.exists():
        try:
            return pd.read_csv(output_path)
        except Exception as e:
            logger.warning("Could not read existing financials.csv: %s", e)
    return pd.DataFrame()


def main() -> None:
    args = sys.argv[1:]
    replace_mode = False

    if args and args[0] == "--replace":
        replace_mode = True
        args = args[1:]

    tickers = args if args else DEFAULT_TICKERS
    logger.info("Starting fetch for tickers: %s (replace_mode=%s)", tickers, replace_mode)

    new_data = fetch_all(tickers)

    output_path = PROCESSED_DIR / "financials.csv"

    if replace_mode:
        combined = new_data
        logger.info("Replace mode: writing only fetched tickers to %s", output_path)
    else:
        existing = _load_existing_financials()
        if not existing.empty:
            # Remove any existing rows for the tickers we just fetched (to update them)
            existing = existing[~existing["ticker"].isin(tickers)]
            combined = pd.concat([existing, new_data], ignore_index=True)
            logger.info(
                "Merge mode: preserved %d existing tickers, updated %d fetched tickers",
                existing["ticker"].nunique(),
                new_data["ticker"].nunique() if not new_data.empty else 0,
            )
        else:
            combined = new_data
            logger.info("No existing financials.csv found, writing new data")

    combined.to_csv(output_path, index=False)

    logger.info(
        "Done. %d records saved to %s covering tickers: %s",
        len(combined),
        output_path,
        sorted(combined["ticker"].unique().tolist()),
    )
    logger.info(
        "Review data/raw_cache/*.csv if any fields look wrong, and check "
        "the warnings above for unmapped row labels or empty statements."
    )


if __name__ == "__main__":
    main()