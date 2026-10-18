"""
Test suite for finance_logic.py
"""

import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from finance_logic import (
    load_financials,
    pivot_to_wide,
    safe_divide,
    compute_working_capital_metrics,
    validate_metrics,
    build_metrics_table
)


class TestFinanceLogic(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        # Create sample long-format financial data with all required statements
        # Each ticker/year combination needs all statement types
        self.sample_data = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST',
                      'TEST', 'TEST', 'TEST', 'TEST'],
            'statement': ['balance_sheet', 'balance_sheet', 'balance_sheet', 'balance_sheet',
                         'balance_sheet', 'balance_sheet', 'income_stmt', 'income_stmt',
                         'income_stmt', 'income_stmt', 'income_stmt', 'income_stmt'],
            'fiscal_year': [2020, 2020, 2020, 2020, 2021, 2021, 2020, 2020, 2021, 2021, 2021, 2021],
            'field': [
                'accounts_receivable', 'accounts_payable', 'inventory', 'current_assets',
                'current_liabilities', 'cash', 'revenue', 'cogs', 'revenue', 'cogs',
                'net_income', 'cogs'
            ],
            'value': [100, 50, 75, 200, 100, 50, 1000, 600, 1200, 720, 100, 720]
        })

    def test_load_financials(self):
        """Test loading financials from CSV"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            self.sample_data.to_csv(f.name, index=False)
            try:
                df = load_financials(f.name)
                pd.testing.assert_frame_equal(df, self.sample_data)
            finally:
                os.unlink(f.name)

    def test_pivot_to_wide(self):
        """Test pivoting long-format to wide-format"""
        # Create test data with unique field/year combinations to avoid pivot conflicts
        test_data = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST',
                      'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST'],
            'statement': ['balance_sheet', 'balance_sheet', 'balance_sheet', 'balance_sheet',
                         'balance_sheet', 'balance_sheet', 'income_stmt', 'income_stmt',
                         'balance_sheet', 'balance_sheet', 'balance_sheet', 'balance_sheet',
                         'balance_sheet', 'balance_sheet', 'income_stmt', 'income_stmt'],
            'fiscal_year': [2020, 2020, 2020, 2020, 2020, 2020, 2020, 2020,
                           2021, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
            'field': [
                'accounts_receivable', 'accounts_payable', 'inventory', 'current_assets',
                'current_liabilities', 'cash', 'revenue', 'cogs',
                'accounts_receivable', 'accounts_payable', 'inventory', 'current_assets',
                'current_liabilities', 'cash', 'revenue', 'cogs'
            ],
            'value': [100, 50, 75, 200, 100, 50, 1000, 600,
                     120, 60, 90, 250, 120, 60, 1200, 720]
        })

        wide_df = pivot_to_wide(test_data)

        # Check shape - should have 2 rows (2020, 2021) and columns for ticker, fiscal_year, plus all unique fields
        self.assertEqual(wide_df.shape[0], 2)  # 2 years

        # Check specific values exist
        self.assertIn('accounts_receivable', wide_df.columns)
        self.assertIn('accounts_payable', wide_df.columns)
        self.assertIn('inventory', wide_df.columns)
        self.assertIn('current_assets', wide_df.columns)
        self.assertIn('current_liabilities', wide_df.columns)
        self.assertIn('cash', wide_df.columns)
        self.assertIn('revenue', wide_df.columns)
        self.assertIn('cogs', wide_df.columns)

        # Check specific values
        self.assertEqual(wide_df.loc[wide_df['fiscal_year'] == 2020, 'accounts_receivable'].iloc[0], 100)
        self.assertEqual(wide_df.loc[wide_df['fiscal_year'] == 2021, 'accounts_receivable'].iloc[0], 120)
        self.assertEqual(wide_df.loc[wide_df['fiscal_year'] == 2020, 'revenue'].iloc[0], 1000)
        self.assertEqual(wide_df.loc[wide_df['fiscal_year'] == 2021, 'revenue'].iloc[0], 1200)

    def test_safe_divide(self):
        """Test safe division function"""
        numerator = pd.Series([10, 20, 0, 30])
        denominator = pd.Series([2, 0, 5, 0])

        result = safe_divide(numerator, denominator)

        # Check results
        self.assertEqual(result.iloc[0], 5.0)   # 10/2
        self.assertTrue(np.isnan(result.iloc[1]))  # 20/0 -> NaN
        self.assertEqual(result.iloc[2], 0.0)   # 0/5
        self.assertTrue(np.isnan(result.iloc[3]))  # 30/0 -> NaN

    def test_compute_working_capital_metrics(self):
        """Test computation of working capital metrics"""
        # Create test data with unique field/year combinations to avoid pivot conflicts
        test_data = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST',
                      'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST', 'TEST'],
            'statement': ['balance_sheet', 'balance_sheet', 'balance_sheet', 'balance_sheet',
                         'balance_sheet', 'balance_sheet', 'income_stmt', 'income_stmt',
                         'balance_sheet', 'balance_sheet', 'balance_sheet', 'balance_sheet',
                         'balance_sheet', 'balance_sheet', 'income_stmt', 'income_stmt'],
            'fiscal_year': [2020, 2020, 2020, 2020, 2020, 2020, 2020, 2020,
                           2021, 2021, 2021, 2021, 2021, 2021, 2021, 2021],
            'field': [
                'accounts_receivable', 'accounts_payable', 'inventory', 'current_assets',
                'current_liabilities', 'cash', 'revenue', 'cogs',
                'accounts_receivable', 'accounts_payable', 'inventory', 'current_assets',
                'current_liabilities', 'cash', 'revenue', 'cogs'
            ],
            'value': [100, 50, 75, 200, 100, 50, 1000, 600,
                     120, 60, 90, 250, 120, 60, 1200, 720]
        })

        # First pivot to wide format
        wide_df = pivot_to_wide(test_data)

        # Compute metrics
        result_df = compute_working_capital_metrics(wide_df)

        # Check that metrics were computed
        self.assertIn('dso', result_df.columns)
        self.assertIn('dpo', result_df.columns)
        self.assertIn('dio', result_df.columns)
        self.assertIn('ccc', result_df.columns)
        self.assertIn('current_ratio', result_df.columns)
        self.assertIn('quick_ratio', result_df.columns)
        self.assertIn('working_capital_requirement', result_df.columns)
        self.assertIn('revenue_growth', result_df.columns)

        # Check specific calculations for 2020
        # DSO = AR / Revenue * 365 = 100/1000 * 365 = 36.5
        expected_dso_2020 = 100 / 1000 * 365
        self.assertAlmostEqual(result_df.loc[result_df['fiscal_year'] == 2020, 'dso'].iloc[0], expected_dso_2020, places=1)

        # Current Ratio = Current Assets / Current Liabilities = 200/100 = 2.0
        current_ratio = result_df.loc[result_df['fiscal_year'] == 2020, 'current_ratio'].iloc[0]
        self.assertFalse(np.isnan(current_ratio), "Current ratio should not be NaN")
        self.assertAlmostEqual(current_ratio, 2.0, places=1)

    def test_validate_metrics(self):
        """Test validation of metrics"""
        # Create test data with some issues
        # We need to make sure all arrays are the same length
        # Create 6 rows: 3 years (2020, 2021, 2022) x 2 statement types
        test_data = pd.DataFrame({
            'ticker': ['TEST'] * 6,
            'statement': ['balance_sheet', 'balance_sheet', 'balance_sheet',
                         'income_stmt', 'income_stmt', 'income_stmt'],
            'fiscal_year': [2020, 2021, 2022, 2020, 2021, 2022],
            'field': ['accounts_receivable', 'accounts_receivable', 'accounts_receivable',
                     'revenue', 'revenue', 'revenue'],
            'value': [100, 150, -50, 1000, 1200, 4000]  # 2022 has negative AR and >200% growth
        })

        # Add the rest of the required fields for each year/statement combination
        # We need 6 additional rows to match the structure
        additional_data = pd.DataFrame({
            'ticker': ['TEST'] * 6,
            'statement': ['balance_sheet', 'balance_sheet', 'balance_sheet',
                         'income_stmt', 'income_stmt', 'income_stmt'],
            'fiscal_year': [2020, 2021, 2022, 2020, 2021, 2022],
            'field': ['accounts_payable', 'inventory', 'current_assets',
                     'current_liabilities', 'cash', 'cogs'],
            'value': [50, 75, 200, 100, 50, 600]
        })

        test_data = pd.concat([test_data, additional_data], ignore_index=True)

        # Add net_income for income statement (3 rows, one per year)
        net_income_data = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'TEST'],
            'statement': ['income_stmt', 'income_stmt', 'income_stmt'],
            'fiscal_year': [2020, 2021, 2022],
            'field': ['net_income', 'net_income', 'net_income'],
            'value': [100, 110, 150]
        })

        test_data = pd.concat([test_data, net_income_data], ignore_index=True)

        # First compute metrics
        wide_df = pivot_to_wide(test_data)

        # Validate
        validation_report = validate_metrics(wide_df)

        # Should have found issues
        self.assertFalse(validation_report.empty)
        self.assertGreater(len(validation_report), 0)

        # Check for specific issue types
        issues = validation_report['issue'].tolist()
        self.assertTrue(any('Negative accounts_receivable' in issue for issue in issues))

    def test_build_metrics_table(self):
        """Test the end-to-end build_metrics_table function"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            self.sample_data.to_csv(f.name, index=False)
            try:
                metrics_df, validation_report = build_metrics_table(f.name)

                # Check that we got DataFrames back
                self.assertIsInstance(metrics_df, pd.DataFrame)
                self.assertIsInstance(validation_report, pd.DataFrame)

                # Check that metrics has expected columns
                expected_columns = ['ticker', 'fiscal_year', 'revenue', 'cogs',
                                  'accounts_receivable', 'accounts_payable', 'inventory',
                                  'current_assets', 'current_liabilities', 'cash',
                                  'dso', 'dpo', 'dio', 'ccc', 'current_ratio',
                                  'quick_ratio', 'working_capital_requirement', 'revenue_growth']

                for col in expected_columns:
                    self.assertIn(col, metrics_df.columns)

            finally:
                os.unlink(f.name)


if __name__ == '__main__':
    unittest.main()