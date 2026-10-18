"""
config.py

Configuration module for the Working Capital & Cash Flow Forecasting tool.
Centralizes constants and configuration values for easy modification.
"""

# Scenario presets - all deltas are applied on TOP of the base case's own trend-derived assumptions.
SCENARIO_PRESETS = {
    "worst": {
        "revenue_growth_delta": -0.05,   # -5 pp vs base growth rate
        "dso_delta_days": +15,           # collections slow down
        "dpo_delta_days": -10,           # pay suppliers faster (worse for cash)
        "dio_delta_days": +10,           # inventory turns slower
        "opex_ratio_delta": +0.03,       # opex as % of revenue rises
    },
    "base": {
        "revenue_growth_delta": 0.0,
        "dso_delta_days": 0,
        "dpo_delta_days": 0,
        "dio_delta_days": 0,
        "opex_ratio_delta": 0.0,
    },
    "best": {
        "revenue_growth_delta": +0.10,   # +10 pp vs base growth rate
        "dso_delta_days": -5,            # collections speed up
        "dpo_delta_days": +10,           # better supplier terms (good for cash)
        "dio_delta_days": -5,            # inventory turns faster
        "opex_ratio_delta": -0.02,       # opex as % of revenue falls
    },
}

# Default tickers for data fetching
DEFAULT_TICKERS = ["PG", "NKE", "MSFT"]

# Monte Carlo simulation defaults
MONTE_CARLO_DEFAULTS = {
    "n_simulations": 5000,
    "growth_std": 0.05,
    "dso_std_days": 5.0,
    "random_seed": 42,
}

# Validation thresholds
VALIDATION_THRESHOLDS = {
    "max_revenue_growth": 2.0,           # >200% YoY change
    "max_ccc_days": 365,                 # CCC out of plausible range
}

# Default forecast horizon (in months)
DEFAULT_FORECAST_HORIZON_MONTHS = 12

# Days in year for financial calculations
DAYS_IN_YEAR = 365