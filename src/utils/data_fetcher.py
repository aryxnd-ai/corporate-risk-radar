"""
Financial Data Fetcher
========================
Retrieves and normalises financial metrics from Yahoo Finance via yfinance.
Handles missing data gracefully — many metrics are unavailable for smaller
or non-US companies and we must not crash on None values.
"""

import yfinance as yf
import pandas as pd
from typing import Optional
import warnings
warnings.filterwarnings("ignore")


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
    except (TypeError, ValueError):
        return None


def _derive_metrics(info: dict) -> dict:
    """Compute derived ratios not directly provided by yfinance."""
    derived = {}

    total_revenue      = _safe_get(info, "totalRevenue")
    total_assets       = _safe_get(info, "totalAssets")
    operating_cf       = _safe_get(info, "operatingCashflow")
    profit_margins     = _safe_get(info, "profitMargins")
    current_assets     = _safe_get(info, "totalCurrentAssets")
    current_liabilities= _safe_get(info, "totalCurrentLiabilities")
    total_assets_      = _safe_get(info, "totalAssets")

    # Asset Turnover = Revenue / Total Assets
    if total_revenue and total_assets and total_assets != 0:
        derived["assetTurnover"] = total_revenue / total_assets

    # Operating CF Margin = Operating CF / Revenue
    if operating_cf and total_revenue and total_revenue != 0:
        derived["operatingCashflowRatio"] = operating_cf / total_revenue

    # Working Capital Ratio = (Current Assets - Current Liabilities) / Total Assets
    if current_assets and current_liabilities and total_assets_:
        wc = current_assets - current_liabilities
        derived["workingCapitalRatio"] = wc / total_assets_ if total_assets_ != 0 else None

    # Debt to EBITDA proxy
    total_debt = _safe_get(info, "totalDebt")
    ebitda     = _safe_get(info, "ebitda")
    if total_debt and ebitda and ebitda > 0:
        derived["debtToEbitda"] = total_debt / ebitda

    return derived


def fetch_company_data(ticker: str) -> dict:
    """
    Fetch all financial metrics for a given ticker symbol.
    Returns a flat dict of metric_name -> float|None.
    """
    try:
        t    = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        print(f"  [!] Failed to fetch {ticker}: {e}")
        return {}

    base = {key: _safe_get(info, key) for key in METRIC_KEYS}

    # Company metadata
    base["name"]     = info.get("longName") or info.get("shortName") or ticker
    base["sector"]   = info.get("sector", "Unknown")
    base["industry"] = info.get("industry", "Unknown")
    base["country"]  = info.get("country", "Unknown")
    base["currency"] = info.get("currency", "USD")
    base["website"]  = info.get("website", "")
    base["ticker"]   = ticker.upper()

    # Derived
    base.update(_derive_metrics(info))

    return base


def fetch_multiple(tickers: list, verbose: bool = True) -> dict:
    """Fetch data for a list of tickers. Returns {ticker: metrics_dict}."""
    results = {}
    for t in tickers:
        if verbose:
            print(f"  Fetching {t}...")
        data = fetch_company_data(t)
        if data:
            results[t.upper()] = data
    return results


def metrics_to_dataframe(results: dict) -> pd.DataFrame:
    """Convert the nested results dict to a flat DataFrame."""
    rows = []
    for ticker, m in results.items():
        row = {"ticker": ticker}
        row.update({k: v for k, v in m.items() if k not in ("name", "sector", "industry", "country", "currency", "website", "ticker")})
        rows.append(row)
    return pd.DataFrame(rows)
