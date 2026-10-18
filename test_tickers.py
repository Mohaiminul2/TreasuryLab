"""
test_tickers.py

Run this FIRST on your local machine, before anything else, to confirm
yfinance can actually reach Yahoo's servers from your network and that
your chosen tickers return usable data.

Usage:
    python test_tickers.py
    python test_tickers.py PG NKE MSFT GOOGL
"""

import sys
import yfinance as yf

from config import DEFAULT_TICKERS


def test_ticker(ticker: str):
    print(f"\n{'=' * 50}")
    print(f"Testing: {ticker}")
    print("=" * 50)

    t = yf.Ticker(ticker)

    for label, attr in [
        ("Balance Sheet", "balance_sheet"),
        ("Income Statement", "income_stmt"),
        ("Cash Flow", "cashflow"),
    ]:
        try:
            df = getattr(t, attr)
            if df is None or df.empty:
                print(f"  [FAIL] {label}: EMPTY — consider a different ticker")
            else:
                print(f"  [OK]   {label}: {df.shape[0]} line items x {df.shape[1]} years")
                print(f"         Years available: {[c.year for c in df.columns]}")
        except Exception as e:
            print(f"  [ERROR] {label}: {e}")


def main():
    tickers = sys.argv[1:] if len(sys.argv) > 1 else DEFAULT_TICKERS
    print(f"Testing tickers: {tickers}")
    print("If you see [FAIL] or [ERROR] for any ticker, swap it for another")
    print("large-cap, long-listed company before proceeding to the full build.\n")

    for ticker in tickers:
        test_ticker(ticker)

    print(f"\n{'=' * 50}")
    print("Done. If all three statements show [OK] for at least 2-3 tickers,")
    print("you're ready to run: python data_fetcher.py")
    print("=" * 50)


if __name__ == "__main__":
    main()
