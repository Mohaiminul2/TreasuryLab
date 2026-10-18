"""
Test suite for forecasting.py
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import os

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from forecasting import (
    get_base_growth_rate,
    custom_scenario,
    forecast_scenarios,
    monte_carlo_base_case
)
from finance_logic import compute_working_capital_metrics, pivot_to_wide


class TestForecasting(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        # Create sample metrics data similar to what finance_logic.py produces
        self.sample_metrics = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'TEST'],
            'fiscal_year': [2019, 2020, 2021],
            'revenue': [1000, 1100, 1200],
            'cogs': [600, 660, 720],
            'net_income': [100, 110, 120],
            'accounts_receivable': [100, 110, 120],
            'inventory': [150, 165, 180],
            'accounts_payable': [80, 88, 96],
            'working_capital_requirement': [170, 187, 204],  # AR + Inv - AP
            'dso': [36.5, 36.5, 36.5],  # 100/1000*365, etc.
            'dpo': [48.7, 48.7, 48.7],  # 80/600*365, etc.
            'dio': [91.3, 91.3, 91.3],  # 150/600*365, etc.
            'ccc': [-12.5, -12.5, -12.5],  # DSO + DIO - DPO
            'revenue_growth': [np.nan, 0.1, 0.0909090909090909],  # YoY growth: 2020: 10%, 2021: ~9.09%
        })

    def test_get_base_growth_rate(self):
        """Test getting base growth rate"""
        growth_rate = get_base_growth_rate(self.sample_metrics)
        # Historical growth: (1100-1000)/1000 = 0.1, (1200-1100)/1100 = 0.0909
        # Average = (0.1 + 0.0909)/2 = 0.09545
        self.assertAlmostEqual(growth_rate, 0.09545, places=4)

    def test_get_base_growth_rate_no_history(self):
        """Test getting base growth rate with no historical data"""
        single_year_df = self.sample_metrics[self.sample_metrics['fiscal_year'] == 2021].copy()
        growth_rate = get_base_growth_rate(single_year_df)
        # Should fall back to 3%
        self.assertEqual(growth_rate, 0.03)

    def test_custom_scenario(self):
        """Test custom scenario calculation"""
        result = custom_scenario(
            self.sample_metrics,
            ticker='TEST',
            growth_adj_pp=5.0,  # +5 percentage points
            dso_adj_days=5.0,   # +5 days
            dpo_adj_days=0.0,
            dio_adj_days=0.0,
            opex_adj_pp=0.0,
            horizon_months=12
        )

        # Check that we got a result dict
        self.assertIsInstance(result, dict)
        self.assertEqual(result['ticker'], 'TEST')
        self.assertEqual(result['scenario'], 'custom')
        self.assertEqual(result['forecast_year'], 2022)  # 2021 + 1 year

        # Check that revenue grew with the adjustment
        # Base growth rate should be ~9.545%, plus 5% = ~14.545%
        # 2021 revenue: 1200
        # Expected: 1200 * (1 + 0.14545) = ~1374.54
        self.assertAlmostEqual(result['revenue'], 1200 * (1 + 0.09545 + 0.05), places=1)

    def test_forecast_scenarios(self):
        """Test forecast scenarios function"""
        forecast_df = forecast_scenarios(
            self.sample_metrics,
            ticker='TEST',
            horizon_months=12
        )

        # Check that we got a DataFrame
        self.assertIsInstance(forecast_df, pd.DataFrame)
        # Should have 3 rows (worst, base, best)
        self.assertEqual(len(forecast_df), 3)
        # Check required columns exist
        required_columns = ['ticker', 'scenario', 'forecast_year', 'revenue',
                          'cogs', 'dso', 'dpo', 'dio', 'ccc',
                          'accounts_receivable', 'inventory', 'accounts_payable',
                          'working_capital_requirement', 'operating_cf_estimate', 'cash_flag']
        for col in required_columns:
            self.assertIn(col, forecast_df.columns)

        # Check scenario names
        scenarios = forecast_df['scenario'].tolist()
        self.assertIn('worst', scenarios)
        self.assertIn('base', scenarios)
        self.assertIn('best', scenarios)

    def test_monte_carlo_base_case(self):
        """Test Monte Carlo base case function"""
        # Run with fewer simulations for faster testing
        sim_df = monte_carlo_base_case(
            self.sample_metrics,
            ticker='TEST',
            n_simulations=100,  # Reduced for testing
            horizon_months=12
        )

        # Check that we got a DataFrame
        self.assertIsInstance(sim_df, pd.DataFrame)
        # Should have 100 rows (one per simulation)
        self.assertEqual(len(sim_df), 100)
        # Check required columns exist
        self.assertIn('simulation_id', sim_df.columns)
        self.assertIn('operating_cf_estimate', sim_df.columns)
        self.assertIn('shortfall', sim_df.columns)

        # Check that simulation_id is sequential
        expected_ids = list(range(100))
        actual_ids = sim_df['simulation_id'].tolist()
        self.assertEqual(actual_ids, expected_ids)

        # Check that operating_cf_estimate is numeric
        self.assertTrue(pd.api.types.is_numeric_dtype(sim_df['operating_cf_estimate']))

        # Check that shortfall is boolean
        self.assertTrue(pd.api.types.is_bool_dtype(sim_df['shortfall']))


if __name__ == '__main__':
    unittest.main()