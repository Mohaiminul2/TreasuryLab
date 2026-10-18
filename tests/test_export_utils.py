"""
Test suite for export_utils.py
"""

import unittest
import pandas as pd
import numpy as np
import tempfile
import os
from io import BytesIO

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from export_utils import build_excel_report, build_pdf_report


class TestExportUtils(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        # Create sample historical data
        self.historical_df = pd.DataFrame({
            'fiscal_year': [2020, 2021],
            'revenue': [1000000, 1200000],
            'ccc': [30, 25],
            'dso': [45, 40],
            'dpo': [30, 35],
            'dio': [15, 20],
            'current_ratio': [1.5, 1.6]
        })

        # Create sample forecast data
        self.forecast_df = pd.DataFrame({
            'scenario': ['base', 'best', 'worst'],
            'forecast_year': [2022, 2022, 2022],
            'revenue': [1300000, 1400000, 1100000],
            'ccc': [20, 15, 30],
            'operating_cf_estimate': [100000, 150000, 50000],
            'cash_flag': ['OK', 'OK', 'OK']
        })

    def test_build_excel_report(self):
        """Test building Excel report"""
        ticker = "TEST"
        excel_bytes = build_excel_report(ticker, self.historical_df, self.forecast_df)

        # Check that we got bytes back
        self.assertIsInstance(excel_bytes, bytes)
        # Check that it's not empty
        self.assertGreater(len(excel_bytes), 0)

        # Try to read it back as Excel to verify it's valid
        try:
            excel_buffer = BytesIO(excel_bytes)
            # Just check that we can open it without error
            self.assertIsNotNone(excel_buffer)
        except Exception as e:
            self.fail(f"Failed to create valid Excel file: {e}")

    def test_build_pdf_report(self):
        """Test building PDF report"""
        ticker = "TEST"
        pdf_bytes = build_pdf_report(ticker, self.historical_df, self.forecast_df)

        # Check that we got bytes back
        self.assertIsInstance(pdf_bytes, bytes)
        # Check that it's not empty
        self.assertGreater(len(pdf_bytes), 0)

        # Try to verify it starts with PDF header
        self.assertTrue(pdf_bytes.startswith(b'%PDF'), "PDF file should start with %PDF")

    def test_build_excel_report_empty_data(self):
        """Test building Excel report with empty data"""
        ticker = "TEST"
        empty_hist = pd.DataFrame()
        empty_forecast = pd.DataFrame()

        # Should not crash
        excel_bytes = build_excel_report(ticker, empty_hist, empty_forecast)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)

    def test_build_pdf_report_empty_data(self):
        """Test building PDF report with empty data"""
        ticker = "TEST"
        empty_hist = pd.DataFrame()
        empty_forecast = pd.DataFrame()

        # Should not crash
        pdf_bytes = build_pdf_report(ticker, empty_hist, empty_forecast)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)


if __name__ == '__main__':
    unittest.main()