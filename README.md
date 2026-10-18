# TreasuryLab

**Working Capital & Cash Flow Forecasting Tool**

A Dash/Plotly analytics dashboard that forecasts working capital and cash flow needs using real public-company financial statements from Yahoo Finance, and stress-tests those forecasts under Best / Base / Worst case scenarios.

## About

Finance and treasury teams routinely need to answer: *"If our collection period slips, our supplier terms tighten, or demand slows, do we have enough cash?"* This tool operationalizes that question — pulling three financial statements (Income Statement, Balance Sheet, Cash Flow Statement) for a company, computing its working capital cycle (DSO, DPO, DIO, Cash Conversion Cycle), and projecting 12 months forward under configurable and fixed scenario assumptions, flagging any projected cash shortfall. It demonstrates the intersection of MBA-level financial analysis and applied data engineering — not a stock-prediction tool, but a decision-support tool in the FP&A / treasury tradition.

**Target audience:** FP&A analysts, treasury professionals, financial modelers, and students of corporate finance.

## Key Features

- **Automated data pipeline**: Fetches and normalizes annual financial statements from Yahoo Finance via `yfinance`
- **Working capital metrics**: Computes DSO, DPO, DIO, CCC, Current Ratio, Quick Ratio, Working Capital Requirement
- **Scenario engine**: Fixed Best / Base / Worst presets + custom slider-driven forecasts
- **Cash flow projection**: 12-month forward operating cash flow estimates with shortfall risk flagging
- **Probabilistic layer**: Optional Monte Carlo simulation (5,000 runs) over Base case for shortfall probability
- **Cross-company benchmarking**: Compare CCC, liquidity, and day-metrics across loaded tickers
- **Export**: Download historical + forecast data as Excel (.xlsx) or PDF summary
- **Responsive dark/light theme**: Persisted via localStorage, mobile-friendly sidebar/drawer navigation
- **Design-system CSS**: Token-driven theming with automated guard tests
- **Framework-agnostic analytics**: Core modules accept/return plain pandas DataFrames for reusability

## Technology Stack

| Area | Technology |
|------|------------|
| Language | Python 3.10+ |
| Data Source | yfinance (Yahoo Finance) |
| Data Processing | pandas, numpy |
| Web Framework | Dash 4.4 (multi-page, `use_pages=True`) |
| UI Components | dash-bootstrap-components 2.x |
| Visualization | Plotly 5.x |
| Export | openpyxl (Excel), reportlab (PDF) |
| Testing | unittest, pytest (CSS guard) |
| Styling | Custom CSS with design tokens |

### Project Layout

```
treasurylab/
├── app.py                      # Dash entry point (port 8050)
├── config.py                   # Centralized constants (scenarios, tickers, validation)
├── data_fetcher.py             # Pulls & normalizes yfinance data
├── finance_logic.py            # Computes metrics, validates data
├── forecasting.py              # Baseline + scenario forecasts + Monte Carlo
├── export_utils.py             # Excel/PDF report generation
├── test_tickers.py             # Pre-flight ticker validation
├── run_tests.py                # Test runner (unittest + pytest)
├── requirements.txt            # Python dependencies
├── assets/
│   └── custom.css              # Design-system CSS tokens
├── data/
│   ├── raw_cache/              # Per-ticker yfinance raw dumps
│   └── processed/
│       ├── financials.csv      # Long-format normalized data
│       ├── metrics.csv         # Wide metrics table (dashboard input)
│       └── validation_report.csv  # Written only when issues flagged
├── pages/
│   ├── _data_loader.py         # Cached metrics loader with mtime invalidation
│   ├── _ui.py                  # Facade to ui_modules/
│   ├── 1_overview.py           # Revenue/COGS, net margin, balance sheet
│   ├── 2_working_capital.py    # DSO/DPO/DIO, CCC, liquidity ratios
│   ├── 3_forecast.py           # Custom slider-driven forecast
│   ├── 4_scenario_comparison.py # Fixed Best/Base/Worst presets
│   ├── 5_company_comparison.py  # Cross-company benchmarking
│   ├── 6_export.py             # Excel/PDF download
│   └── ui_modules/
│       ├── theme_utils.py      # Theme tokens, normalization
│       ├── formatting_utils.py # Number formatting (money, days, pct, ratio)
│       ├── layout_components.py # Reusable UI primitives
│       └── chart_utils.py      # Plotly colors, templates, defaults
└── tests/
    ├── test_finance_logic.py
    ├── test_forecasting.py
    ├── test_data_loader.py
    ├── test_export_utils.py
    └── test_custom_css.py      # CSS token/selector/brace guard
```

## Prerequisites

- **Python 3.10+** (tested on 3.10.7)
- **pip** (for dependency installation)
- **Internet access** (required for `yfinance` to fetch Yahoo Finance data)

No database, Docker, or external services required.

## Installation

```bash
# 1. Clone the repository
git clone <repository-url>
cd treasurylab

# 2. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip3 install -r requirements.txt
```

## Usage

### 1. Validate Tickers (run once)

```bash
python3 test_tickers.py
# Optional: python3 test_tickers.py PG NKE MSFT GOOGL
```
Confirms Yahoo Finance returns usable data for your tickers. If any shows `[FAIL] EMPTY`, swap it for another large-cap, long-listed company.

### 2. Fetch Financial Statements

```bash
# Default: merges with existing data, updates only specified tickers
python3 data_fetcher.py

# Fetch specific tickers (merge mode)
python3 data_fetcher.py PG NKE

# Full replace (discards other tickers)
python3 data_fetcher.py --replace PG NKE
```

Outputs: `data/raw_cache/{TICKER}_{statement}.csv` + `data/processed/financials.csv`

### 3. Compute Metrics

```bash
python3 finance_logic.py
```

Outputs: `data/processed/metrics.csv` + optional `validation_report.csv`

### 4. Launch Dashboard

```bash
# Production (default): debug=False, no Werkzeug debugger exposed
python3 app.py

# Development: hot-reload + debugger (LAN only)
FLASK_ENV=development python3 app.py
```

Open **http://127.0.0.1:8050** in your browser.


### 5. Refresh Data

After new earnings releases, re-run steps 2–3, then restart `app.py`. The dashboard reads from cached CSVs, not live from yfinance.

## Dashboard Pages

| Page | Route | Description |
|------|-------|-------------|
| **Overview** | `/` | Revenue vs COGS bars, Net Margin % trend, AR/Inventory/AP/Cash trends, raw historical table |
| **Working Capital** | `/working-capital` | DSO/DPO/DIO trend, CCC bars, Current/Quick ratios with 1.0× threshold |
| **Forecast & Assumptions** | `/forecast` | Interactive sliders (±20pp growth, ±30d DSO/DPO/DIO, ±10pp opex) for custom 12-month forecast |
| **Scenario Comparison** | `/scenarios` | Fixed Best/Base/Worst side-by-side (OCF + CCC charts, assumptions table, risk flag) |
| **Company Comparison** | `/compare` | Cross-company benchmarking (CCC, liquidity, day-metrics, latest fiscal year) |
| **Export** | `/export` | Download historical + forecast as Excel (.xlsx) or PDF |

All pages share a persisted dark/light theme, responsive sidebar (desktop) / drawer (mobile), and per-process metrics cache with file-mtime invalidation.

## Data Dictionary (`metrics.csv`)

One row per `(ticker, fiscal_year)`:

| Column | Formula / Meaning |
|--------|-------------------|
| `revenue`, `cogs`, `net_income` | Income statement inputs |
| `accounts_receivable`, `inventory`, `accounts_payable`, `cash` | Balance-sheet WC inputs |
| `current_assets`, `current_liabilities` | Liquidity inputs |
| `dso` | `AR / Revenue × 365` — avg collection days |
| `dpo` | `AP / COGS × 365` — avg payment days |
| `dio` | `Inventory / COGS × 365` — avg inventory days |
| `ccc` | `DSO + DIO − DPO` — cash conversion cycle (days) |
| `current_ratio` | `Current Assets / Current Liabilities` |
| `quick_ratio` | `(Current Assets − Inventory) / Current Liabilities` |
| `working_capital_requirement` | `AR + Inventory − AP` — net operating cash tied up |
| `revenue_growth` | YoY revenue change (Base forecast uses historical mean, fallback 3%) |


## Running Tests

```bash
# Run all tests (unittest + pytest CSS guard)
python3 run_tests.py
```

- **21 unittest tests**: finance logic, forecasting, data loader, export utils
- **5 pytest tests**: CSS brace balance, selector typos, token definitions, theme scopes, offcanvas themes

Exit code `0` = all green.

## Known Limitations

- **yfinance data completeness varies by ticker.** Large, liquid, long-listed companies (defaults: PG/NKE/MSFT) have the most complete fundamentals. Smaller/recently-listed companies may return sparse statements — `data_fetcher.py` logs warnings and skips no-data tickers.
- **Forecasts are scenario-based, not predictive models.** Designed as directional decision-support, not statistical accuracy claims.
- **COGS/margin ratios held constant** from latest fiscal year in scenario engine (except explicit opex adjustment). Appropriate for 12-month horizon.
- **Annual granularity only.** `custom_scenario(horizon_months)` coerces to years via `max(1, round(months/12))`; UI uses fixed 12 months.
- **Single-user CSV datastore.** No file locking or concurrent write safety.
- **No authentication/authorization.** Local tool by design — do not deploy on shared networks without adding auth.

## License

No `LICENSE` file available. 
