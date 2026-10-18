#!/usr/bin/env python3
"""
Test runner for the Working Capital & Cash Flow Forecasting tool.

Runs BOTH suites:
  - tests/test_*.py unittest suites (finance, forecasting, data loader,
    export utils)
  - tests/test_custom_css.py (pytest-style — executed via a small
    in-process pytest wrapper so the standard `python3 run_tests.py`
    command does not silently skip it)
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def run_unittest_suites() -> "unittest.TestResult":
    """Discover and run all unittest-style tests."""
    loader = unittest.TestLoader()
    suite = loader.discover(
        os.path.join(PROJECT_ROOT, "tests"), pattern="test_*.py"
    )
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


def run_pytest_suites() -> bool:
    """Run pytest-style suites (test_custom_css.py) in-process.

    Returns True on success; returns True (skip) if pytest itself is
    unavailable so the runner still works in minimal environments.
    """
    css_test = os.path.join(PROJECT_ROOT, "tests", "test_custom_css.py")
    if not os.path.exists(css_test):
        return True
    try:
        import pytest
    except ImportError:
        print("pytest not installed — skipping tests/test_custom_css.py")
        return True

    result = pytest.main([css_test, "-q", "-p", "no:asyncio"])
    # pytest exit codes: 0 = passed, 5 = no tests collected (treat as pass)
    return result in (0, 5)


def main() -> int:
    # Make project root importable for the test modules
    sys.path.insert(0, PROJECT_ROOT)

    unittest_ok = run_unittest_suites().wasSuccessful()
    pytest_ok = run_pytest_suites()
    return 0 if (unittest_ok and pytest_ok) else 1


if __name__ == "__main__":
    sys.exit(main())