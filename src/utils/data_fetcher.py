"""
Financial Data Fetcher (rate-limit safe)
========================================
Handles Yahoo rate limits with caching + retries.
"""

import yfinance as yf
import pandas as pd
import time
from typing import Optional
import warnings

warnings.filterwarnings("ignore")

# cache results so Yahoo isn't hit repeatedly
_CACHE = {}


METRIC_KEYS = [
    "revenueGrowth",
    "earningsGrowth",
    "profitMargins",
    "operatingMargins",
    "grossMargins",
    "ebitdaMargins",
    "returnOnAssets",
    "returnOnEquity",
    "debtToEquity",
    "currentRatio",
    "quickRatio",
    "beta",
    "trailingPE",
    "forwardPE",
    "priceToBook",
    "enterpriseToEbitda",
    "totalDebt",
    "totalRevenue",
    "marketCap",
    "freeCashflow",
    "operatingCashflow",
    "ebitda",
]


def _safe_get(info: dict, key: str) -> Optional[float]:
    val = info.get(key)

    if val is None or val == "N/A":
        return None

    try:
        return float(val)
    except Exception:
        return None


def fetch_company_data(ticker: str) -> dict:
    ticker = ticker.upper()

    # return cached data
    if ticker in _CACHE:
        return _CACHE[ticker]

    for attempt in range(3):

        try:
            t = yf.Ticker(ticker)

            info = t.get_info()

            if not info:
                raise ValueError("No info returned")

            data = {k: _safe_get(info, k) for k in METRIC_KEYS}

            data["name"] = info.get("longName") or ticker
            data["sector"] = info.get("sector", "Unknown")
            data["industry"] = info.get("industry", "Unknown")
            data["ticker"] = ticker

            _CACHE[ticker] = data

            return data

        except Exception as e:

            # exponential backoff
            time.sleep(2 ** attempt)

    return {}


def fetch_multiple(tickers: list, verbose: bool = True):

    results = {}

    for t in tickers:

        if verbose:
            print(f"Fetching {t}")

        data = fetch_company_data(t)

        if data:
            results[t] = data

        # spacing to avoid Yahoo bans
        time.sleep(1)

    return results


def metrics_to_dataframe(results: dict) -> pd.DataFrame:

    rows = []

    for ticker, metrics in results.items():

        row = {"ticker": ticker}

        for k, v in metrics.items():
            if k not in ("ticker", "name", "sector", "industry"):
                row[k] = v

        rows.append(row)

    return pd.DataFrame(rows)
