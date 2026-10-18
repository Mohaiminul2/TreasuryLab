"""
pages/_data_loader.py

Shared helper used by all Dash pages to load the precomputed metrics
table. Not a page itself (leading underscore keeps Dash's page router
from registering it as one).

Data is loaded once per process into a module-level cache — the Dash
app is expected to be restarted after re-running data_fetcher.py /
finance_logic.py to pick up fresh data.

Enhanced with cache invalidation support for development workflows.
"""

import logging
from pathlib import Path
from typing import Optional
import pandas as pd
import os
import time

logger = logging.getLogger(__name__)

METRICS_PATH = Path("data/processed/metrics.csv")

# Cache storage with metadata for invalidation
_cache = {
    "data": None,
    "timestamp": None,
    "file_mtime": None
}


def _get_file_mtime(file_path: Path) -> Optional[float]:
    """Get file modification time, returning None if file doesn't exist."""
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return None


def _is_cache_valid() -> bool:
    """Check if the cached data is still valid based on file modification time."""
    if _cache["data"] is None:
        return False

    current_mtime = _get_file_mtime(METRICS_PATH)
    if current_mtime is None:
        return False

    return _cache["file_mtime"] == current_mtime


def load_metrics(force_reload: bool = False) -> pd.DataFrame:
    """
    Load the precomputed metrics table, cached for the process lifetime.

    Args:
        force_reload: If True, bypass cache and reload from file

    Returns:
        DataFrame containing the metrics data

    Raises:
        FileNotFoundError: If metrics.csv doesn't exist
    """
    # Check if we need to reload
    if force_reload or not _is_cache_valid():
        if not METRICS_PATH.exists():
            raise FileNotFoundError(
                f"{METRICS_PATH} not found. Run these first:\n"
                "  python data_fetcher.py\n"
                "  python finance_logic.py"
            )

        # Load fresh data
        df = pd.read_csv(METRICS_PATH)

        # Update cache
        _cache["data"] = df
        _cache["timestamp"] = time.time()
        _cache["file_mtime"] = _get_file_mtime(METRICS_PATH)

        logger.info("Loaded metrics.csv: %d rows", len(df))
    else:
        logger.debug("Using cached metrics data")

    return _cache["data"]


def available_tickers() -> list[str]:
    """List of tickers present in the loaded metrics table."""
    df = load_metrics()
    return sorted(df["ticker"].unique().tolist())


def clear_cache() -> None:
    """Clear the cached data. Useful for development or testing."""
    _cache["data"] = None
    _cache["timestamp"] = None
    _cache["file_mtime"] = None
    logger.info("Metrics cache cleared")


def get_cache_info() -> dict:
    """Get information about the current cache state."""
    return {
        "cached": _cache["data"] is not None,
        "rows": len(_cache["data"]) if _cache["data"] is not None else 0,
        "timestamp": _cache["timestamp"],
        "file_mtime": _cache["file_mtime"],
        "current_file_mtime": _get_file_mtime(METRICS_PATH)
    }


def safe_load_metrics() -> pd.DataFrame:
    """
    Load metrics table safely, returning empty DataFrame if file not found.
    Use this in page layouts to avoid crashes when metrics.csv is missing.
    """
    try:
        return load_metrics()
    except FileNotFoundError:
        return pd.DataFrame()


def safe_available_tickers() -> list[str]:
    """
    Return available tickers safely, returning empty list if metrics.csv not found.
    """
    try:
        return available_tickers()
    except FileNotFoundError:
        return []