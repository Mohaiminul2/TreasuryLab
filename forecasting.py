"""
forecasting.py

Forecasting engine for the working capital / cash flow tool.

Approach (deliberately interpretable, not a black-box model — audience
is finance-literate and needs to trust/explain the numbers):
    1. Baseline trend: simple historical average growth rate applied
       forward, per company.
    2. Scenario engine: Best / Base / Worst presets that shift growth
       rate and DSO/DPO/DIO assumptions, then re-derive AR/AP/Inventory/
       Cash and a forecasted operating cash flow from those shifted
       working-capital metrics.
    3. Optional Monte Carlo layer over the Base case for a probabilistic
       cash-shortfall view.

Usage:
    from forecasting import forecast_scenarios
    forecast_df = forecast_scenarios(metrics_df, ticker="PG", horizon_months=12)
"""

import logging
from typing import Dict, Any

import numpy as np
import pandas as pd

from config import (
    SCENARIO_PRESETS,
    DAYS_IN_YEAR,
    DEFAULT_FORECAST_HORIZON_MONTHS,
    MONTE_CARLO_DEFAULTS
)

logger = logging.getLogger(__name__)


def get_base_growth_rate(company_df: pd.DataFrame) -> float:
    """
    Historical average YoY revenue growth rate for a single company,
    used as the Base case forecast assumption. Falls back to 3% (a
    conservative generic assumption) if insufficient history exists.
    """
    growth_series = company_df["revenue_growth"].dropna()
    if len(growth_series) < 2:
        logger.warning(
            "Insufficient historical revenue growth data available for this company — "
            "defaulting Base case growth rate to 3%."
        )
        return 0.03
    return float(growth_series.mean())


def _apply_single_scenario(
    latest: pd.Series,
    base_growth: float,
    forecast_years_ahead: int,
    ticker: str,
    scenario_name: str,
    deltas: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Shared single-scenario core used by both forecast_scenarios() and
    custom_scenario(). Framework-agnostic: pure pandas/numpy, no Dash.
    """
    growth_rate = base_growth + deltas["revenue_growth_delta"]

    # Project revenue forward
    forecast_revenue = latest["revenue"] * (1 + growth_rate) ** forecast_years_ahead

    # COGS assumed to scale with revenue at the historical COGS/Revenue ratio
    historical_cogs_ratio = (
        latest["cogs"] / latest["revenue"] if pd.notna(latest.get("cogs")) and latest.get("revenue") else np.nan
    )
    forecast_cogs = (
        forecast_revenue * historical_cogs_ratio if pd.notna(historical_cogs_ratio) else np.nan
    )

    # Apply scenario deltas to working capital day-metrics
    forecast_dso = (latest["dso"] if pd.notna(latest["dso"]) else 0) + deltas["dso_delta_days"]
    forecast_dpo = (latest["dpo"] if pd.notna(latest["dpo"]) else 0) + deltas["dpo_delta_days"]
    forecast_dio = (latest["dio"] if pd.notna(latest["dio"]) else 0) + deltas["dio_delta_days"]
    forecast_ccc = forecast_dso + forecast_dio - forecast_dpo

    # Re-derive balance sheet working capital items from the day-metrics
    forecast_ar = (forecast_dso / DAYS_IN_YEAR) * forecast_revenue
    forecast_inventory = (
        (forecast_dio / DAYS_IN_YEAR) * forecast_cogs if pd.notna(forecast_cogs) else np.nan
    )
    forecast_ap = (
        (forecast_dpo / DAYS_IN_YEAR) * forecast_cogs if pd.notna(forecast_cogs) else np.nan
    )

    forecast_wcr = forecast_ar + forecast_inventory - forecast_ap

    # Rough operating cash flow estimate:
    # Net margin held at the latest fiscal year's level, minus the CHANGE
    # in WCR (an increase in WCR consumes cash; a decrease releases cash)
    historical_wcr = latest["working_capital_requirement"]
    delta_wcr = forecast_wcr - historical_wcr if pd.notna(historical_wcr) else np.nan

    historical_net_margin = (
        latest["net_income"] / latest["revenue"]
        if "net_income" in latest and pd.notna(latest.get("net_income")) and latest.get("revenue")
        else 0.08  # conservative generic fallback assumption
    )
    opex_adjustment = forecast_revenue * deltas["opex_ratio_delta"]

    forecast_net_income = (forecast_revenue * historical_net_margin) - opex_adjustment
    forecast_operating_cf = forecast_net_income - delta_wcr if pd.notna(delta_wcr) else np.nan

    cash_flag = "SHORTFALL RISK" if pd.notna(forecast_operating_cf) and forecast_operating_cf < 0 else "OK"

    return {
        "ticker": ticker,
        "scenario": scenario_name,
        "forecast_year": int(latest["fiscal_year"]) + forecast_years_ahead,
        "revenue_growth_assumed": growth_rate,
        "revenue": forecast_revenue,
        "cogs": forecast_cogs,
        "dso": forecast_dso,
        "dpo": forecast_dpo,
        "dio": forecast_dio,
        "ccc": forecast_ccc,
        "accounts_receivable": forecast_ar,
        "inventory": forecast_inventory,
        "accounts_payable": forecast_ap,
        "working_capital_requirement": forecast_wcr,
        "delta_wcr_vs_latest": delta_wcr,
        "net_income_estimate": forecast_net_income,
        "operating_cf_estimate": forecast_operating_cf,
        "cash_flag": cash_flag,
    }


def custom_scenario(
    metrics_df: pd.DataFrame,
    ticker: str,
    growth_adj_pp: float = 0.0,
    dso_adj_days: float = 0.0,
    dpo_adj_days: float = 0.0,
    dio_adj_days: float = 0.0,
    opex_adj_pp: float = 0.0,
    horizon_months: int = DEFAULT_FORECAST_HORIZON_MONTHS,
) -> Dict[str, Any]:
    """
    Custom (slider-driven) scenario for a single ticker. Same math as the
    fixed presets, but with caller-supplied deltas in plain units:

        growth_adj_pp / opex_adj_pp: percentage points (e.g. +5 = +0.05)
        dso/dpo/dio_adj_days: days (e.g. +10 = 10 extra days)

    Note: `horizon_months` is coerced to annual granularity via
    `max(1, round(horizon_months / 12))`. Any value 1-17 months yields a
    1-year-ahead forecast; 18-29 months yields 2 years, etc. The UI uses
    a fixed 12-month horizon; this function is provided for API flexibility.

    Returns the same single-row dict shape as one row of forecast_scenarios().
    """
    company_df = metrics_df[metrics_df["ticker"] == ticker].sort_values("fiscal_year")
    if company_df.empty:
        raise ValueError(f"No data found for ticker '{ticker}' in metrics_df.")

    latest = company_df.iloc[-1]
    base_growth = get_base_growth_rate(company_df)
    forecast_years_ahead = max(1, round(horizon_months / 12))

    deltas = {
        "revenue_growth_delta": growth_adj_pp / 100.0,
        "dso_delta_days": dso_adj_days,
        "dpo_delta_days": dpo_adj_days,
        "dio_delta_days": dio_adj_days,
        "opex_ratio_delta": opex_adj_pp / 100.0,
    }
    return _apply_single_scenario(
        latest, base_growth, forecast_years_ahead, ticker, "custom", deltas
    )


def forecast_scenarios(
    metrics_df: pd.DataFrame,
    ticker: str,
    horizon_months: int = DEFAULT_FORECAST_HORIZON_MONTHS,
) -> pd.DataFrame:
    """
    Produce a 12-month-out (or other horizon) forecast under Best/Base/Worst
    scenarios for a single ticker.

    Returns a long-format DataFrame:
        ticker, scenario, forecast_year, revenue, cogs, dso, dpo, dio, ccc,
        accounts_receivable, inventory, accounts_payable,
        working_capital_requirement, operating_cf_estimate, cash_flag
    """
    company_df = metrics_df[metrics_df["ticker"] == ticker].sort_values("fiscal_year")
    if company_df.empty:
        raise ValueError(f"No data found for ticker '{ticker}' in metrics_df.")

    latest = company_df.iloc[-1]
    base_growth = get_base_growth_rate(company_df)
    forecast_years_ahead = max(1, round(horizon_months / 12))

    results = []

    for scenario_name, deltas in SCENARIO_PRESETS.items():
        results.append(
            _apply_single_scenario(
                latest, base_growth, forecast_years_ahead,
                ticker, scenario_name, deltas,
            )
        )

    return pd.DataFrame(results)


def monte_carlo_base_case(
    metrics_df: pd.DataFrame,
    ticker: str,
    n_simulations: int = MONTE_CARLO_DEFAULTS["n_simulations"],
    growth_std: float = MONTE_CARLO_DEFAULTS["growth_std"],
    dso_std_days: float = MONTE_CARLO_DEFAULTS["dso_std_days"],
    horizon_months: int = DEFAULT_FORECAST_HORIZON_MONTHS,
    random_seed: int = MONTE_CARLO_DEFAULTS["random_seed"],
) -> pd.DataFrame:
    """
    Probabilistic layer on top of the Base case: randomly perturbs revenue
    growth and DSO within a normal distribution to produce a distribution
    of possible operating cash flow outcomes, rather than a single point
    estimate.

    Returns a DataFrame with one row per simulation:
        simulation_id, operating_cf_estimate, shortfall (bool)
    """
    rng = np.random.default_rng(random_seed)

    company_df = metrics_df[metrics_df["ticker"] == ticker].sort_values("fiscal_year")
    if company_df.empty:
        raise ValueError(f"No data found for ticker '{ticker}' in metrics_df.")

    latest = company_df.iloc[-1]
    base_growth = get_base_growth_rate(company_df)
    forecast_years_ahead = max(1, round(horizon_months / 12))

    historical_cogs_ratio = (
        latest["cogs"] / latest["revenue"] if pd.notna(latest.get("cogs")) and latest.get("revenue") else np.nan
    )
    historical_net_margin = (
        latest["net_income"] / latest["revenue"]
        if "net_income" in latest and pd.notna(latest.get("net_income")) and latest.get("revenue")
        else 0.08
    )
    historical_wcr = latest["working_capital_requirement"]
    base_dso = latest["dso"] if pd.notna(latest["dso"]) else 0
    base_dpo = latest["dpo"] if pd.notna(latest["dpo"]) else 0
    base_dio = latest["dio"] if pd.notna(latest["dio"]) else 0

    simulated_growth = rng.normal(loc=base_growth, scale=growth_std, size=n_simulations)
    simulated_dso_shift = rng.normal(loc=0, scale=dso_std_days, size=n_simulations)

    results = []
    for i in range(n_simulations):
        growth_rate = simulated_growth[i]
        forecast_revenue = latest["revenue"] * (1 + growth_rate) ** forecast_years_ahead
        forecast_cogs = (
            forecast_revenue * historical_cogs_ratio if pd.notna(historical_cogs_ratio) else np.nan
        )

        forecast_dso = base_dso + simulated_dso_shift[i]
        forecast_ar = (forecast_dso / DAYS_IN_YEAR) * forecast_revenue
        forecast_inventory = (
            (base_dio / DAYS_IN_YEAR) * forecast_cogs if pd.notna(forecast_cogs) else np.nan
        )
        forecast_ap = (
            (base_dpo / DAYS_IN_YEAR) * forecast_cogs if pd.notna(forecast_cogs) else np.nan
        )
        forecast_wcr = forecast_ar + forecast_inventory - forecast_ap
        delta_wcr = forecast_wcr - historical_wcr if pd.notna(historical_wcr) else np.nan

        forecast_net_income = forecast_revenue * historical_net_margin
        forecast_operating_cf = forecast_net_income - delta_wcr if pd.notna(delta_wcr) else np.nan

        results.append({
            "simulation_id": i,
            "operating_cf_estimate": forecast_operating_cf,
            "shortfall": bool(pd.notna(forecast_operating_cf) and forecast_operating_cf < 0),
        })

    sim_df = pd.DataFrame(results)
    shortfall_prob = sim_df["shortfall"].mean()
    logger.info(
        "[%s] Monte Carlo (%d sims): estimated shortfall probability = %.1f%%",
        ticker, n_simulations, shortfall_prob * 100,
    )
    return sim_df


if __name__ == "__main__":
    import logging as _logging
    _logging.basicConfig(level=_logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    from finance_logic import build_metrics_table

    metrics_df, _ = build_metrics_table()

    for ticker in metrics_df["ticker"].unique():
        forecast_df = forecast_scenarios(metrics_df, ticker=ticker, horizon_months=12)
        print(f"\n--- {ticker} scenario forecast ---")
        print(forecast_df[["scenario", "forecast_year", "revenue", "ccc", "operating_cf_estimate", "cash_flag"]])