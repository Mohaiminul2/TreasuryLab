"""
Test suite for _data_loader.py caching functionality
"""

import unittest
import pandas as pd
import tempfile
import os
from pathlib import Path
import time

# Import the module to test
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pages._data_loader import load_metrics, available_tickers, clear_cache, get_cache_info


class TestDataLoader(unittest.TestCase):

    def setUp(self):
        """Set up test data"""
        # Create a temporary metrics.csv file
        self.test_dir = tempfile.mkdtemp()
        self.metrics_path = Path(self.test_dir) / "metrics.csv"

        # Create test data
        self.test_data = pd.DataFrame({
            'ticker': ['TEST', 'TEST', 'OTHER', 'OTHER'],
            'fiscal_year': [2020, 2021, 2020, 2021],
            'revenue': [1000, 1100, 2000, 2200],
            'cogs': [600, 660, 1200, 1320]
        })

        # Save to temporary location
        self.test_data.to_csv(self.metrics_path, index=False)

        # Temporarily override the METRICS_PATH
        import pages._data_loader as dl
        self.original_path = dl.METRICS_PATH
        dl.METRICS_PATH = self.metrics_path

        # Clear cache to start fresh
        clear_cache()

    def tearDown(self):
        """Clean up test data"""
        # Restore original path
        import pages._data_loader as dl
        dl.METRICS_PATH = self.original_path

        # Remove test files
        import shutil
        shutil.rmtree(self.test_dir)

    def test_load_metrics(self):
        """Test loading metrics data"""
        df = load_metrics()
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 4)
        self.assertIn('ticker', df.columns)
        self.assertIn('fiscal_year', df.columns)
        self.assertIn('revenue', df.columns)
        self.assertIn('cogs', df.columns)

    def test_available_tickers(self):
        """Test getting available tickers"""
        tickers = available_tickers()
        self.assertEqual(tickers, ['OTHER', 'TEST'])

    def test_caching_works(self):
        """Test that caching prevents reloading"""
        # Load data first time
        df1 = load_metrics()
        cache_info1 = get_cache_info()

        # Load data second time (should use cache)
        df2 = load_metrics()
        cache_info2 = get_cache_info()

        # Data should be the same
        pd.testing.assert_frame_equal(df1, df2)

        # Cache should be valid
        self.assertTrue(cache_info2['cached'])
        self.assertEqual(cache_info1['timestamp'], cache_info2['timestamp'])

    def test_cache_invalidation(self):
        """Test that cache is invalidated when file changes"""
        # Load initial data
        df1 = load_metrics()
        cache_info1 = get_cache_info()

        # Wait a moment to ensure file modification time will be different
        time.sleep(0.1)

        # Modify the file
        new_data = self.test_data.copy()
        new_data.loc[0, 'revenue'] = 9999  # Change one value
        new_data.to_csv(self.metrics_path, index=False)

        # Load data again (should detect file change and reload)
        df2 = load_metrics()
        cache_info2 = get_cache_info()

        # Data should be different
        self.assertNotEqual(df1.iloc[0]['revenue'], df2.iloc[0]['revenue'])

        # Cache should have been invalidated and reloaded
        self.assertNotEqual(cache_info1['timestamp'], cache_info2['timestamp'])

    def test_force_reload(self):
        """Test force reload parameter"""
        # Load data first time
        df1 = load_metrics()

        # Modify the file
        new_data = self.test_data.copy()
        new_data.loc[0, 'revenue'] = 8888  # Change one value
        new_data.to_csv(self.metrics_path, index=False)

        # Load with force reload (should get new data)
        df2 = load_metrics(force_reload=True)
        self.assertEqual(df2.iloc[0]['revenue'], 8888)  # Should be new value
        self.assertNotEqual(df1.iloc[0]['revenue'], df2.iloc[0]['revenue'])

    def test_clear_cache(self):
        """Test clearing the cache"""
        # Load data to populate cache
        load_metrics()
        cache_info1 = get_cache_info()
        self.assertTrue(cache_info1['cached'])

        # Clear cache
        clear_cache()
        cache_info2 = get_cache_info()
        self.assertFalse(cache_info2['cached'])
        # After clearing, data should be None, so rows should be 0
        self.assertEqual(cache_info2['rows'], 0)


if __name__ == '__main__':
    unittest.main()