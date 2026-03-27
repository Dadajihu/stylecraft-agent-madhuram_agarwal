"""
Data loading module for RetailMind Product Intelligence Agent.
Loads and caches product and review data from CSV files.
"""

import os
import pandas as pd
from config import PRODUCTS_CSV, REVIEWS_CSV

# Module-level cache: DataFrames are loaded once and reused across the app
_products_df = None
_reviews_df = None


def _resolve_csv_path(primary: str) -> str:
    """Try the primary CSV path; if not found, try without 'Set-B ' prefix or with it."""
    if os.path.exists(primary):
        return primary
    # Try alternate name (with or without Set-B prefix)
    alt = primary.replace("Set-B ", "") if "Set-B" in primary else f"Set-B {primary}"
    if os.path.exists(alt):
        return alt
    return primary  # Fall back to original (will raise FileNotFoundError)


def get_products_df() -> pd.DataFrame:
    """Load and return the products DataFrame. Cached after first load."""
    global _products_df
    if _products_df is None:
        _products_df = pd.read_csv(_resolve_csv_path(PRODUCTS_CSV))
    return _products_df


def get_reviews_df() -> pd.DataFrame:
    """Load and return the reviews DataFrame. Cached after first load."""
    global _reviews_df
    if _reviews_df is None:
        _reviews_df = pd.read_csv(_resolve_csv_path(REVIEWS_CSV))
    return _reviews_df
