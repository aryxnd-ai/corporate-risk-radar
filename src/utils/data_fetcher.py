"""
Financial Data Fetcher
========================
Retrieves and normalises financial metrics from Yahoo Finance via yfinance.
Handles missing data gracefully so missing fields do not crash the app.
Also accepts either a list of tickers or a comma-separated ticker string.
"""

from typing import Optional, Union, Iterable
import warnings

import pandas as pd
import yfinance as yf

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
    """Safely convert a Yahoo Finance info field to float."""
    val = info.get(key)
    if val is None or val == "N/A":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _clean_ticker(ticker: str) -> str:
    """Normalize a single ticker."""
    return str(ticker).strip().upper()


def _normalize_tickers(tickers: Union[str, Iterable]) -> list[str]:
    """
    Accept either:
    - "AAPL, MSFT, TSLA"
    - ["AAPL", "MSFT", "TSLA"]
    and return a clean list of tickers.
    """
    if tickers is None:
        return []

    if isinstance(tickers, str):
        raw = tickers.split(",")
    else:
        raw = list(tickers)

    cleaned = []
    for t in raw:
        symbol = _clean_ticker(t)
        if symbol:
            cleaned.append(symbol)

    # remove duplicates while preserving order
    seen = set()
    unique = []
    for t in cleaned:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


def _derive_metrics(info: dict) -> dict:
    """Compute derived ratios not directly provided by yfinance."""
    derived = {}

    total_revenue = _safe_get(info, "totalRevenue")
    total_assets = _safe_get(info, "totalAssets")
    operating_cf = _safe_get(info, "operatingCashflow")
    current_assets = _safe_get(info, "totalCurrentAssets")
    current_liabilities = _safe_get(info, "totalCurrentLiabilities")
    total_debt = _safe_get(info, "totalDebt")
    ebitda = _safe_get(info, "ebitda")

    # Asset Turnover = Revenue / Total Assets
    if total_revenue is not None and total_assets not in (None, 0):
        derived["assetTurnover"] = total_revenue / total_assets
    else:
        derived["assetTurnover"] = None

    # Operating CF Margin = Operating CF / Revenue
    if operating_cf is not None and total_revenue not in (None, 0):
        derived["operatingCashflowRatio"] = operating_cf / total_revenue
    else:
        derived["operatingCashflowRatio"] = None

    # Working Capital Ratio = (Current Assets - Current Liabilities) / Total Assets
    if (
        current_assets is not None
        and current_liabilities is not None
        and total_assets not in (None, 0)
    ):
        wc = current_assets - current_liabilities
        derived["workingCapitalRatio"] = wc / total_assets
    else:
        derived["workingCapitalRatio"] = None

    # Debt to EBITDA
    if total_debt is not None and ebitda not in (None, 0) and ebitda > 0:
        derived["debtToEbitda"] = total_debt / ebitda
    else:
        derived["debtToEbitda"] = None

    return derived


def fetch_company_data(ticker: str) -> dict:
    """
    Fetch all financial metrics for a given ticker symbol.
    Returns a flat dict of metric_name -> float|None plus metadata.
    Returns {} if the ticker cannot be fetched.
    """
    ticker = _clean_ticker(ticker)
    if not ticker:
        return {}

    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
    except Exception as e:
        print(f"[!] Failed to fetch {ticker}: {e}")
        return {}

    # If Yahoo returns basically nothing, treat it as invalid / unavailable
    if not info or not isinstance(info, dict):
        return {}

    base = {key: _safe_get(info, key) for key in METRIC_KEYS}

    # Company metadata
    base["name"] = info.get("longName") or info.get("shortName") or ticker
    base["sector"] = info.get("sector") or "Unknown"
    base["industry"] = info.get("industry") or "Unknown"
    base["country"] = info.get("country") or "Unknown"
    base["currency"] = info.get("currency") or "USD"
    base["website"] = info.get("website") or ""
    base["ticker"] = ticker

    # Derived metrics
    base.update(_derive_metrics(info))

    # Minimal validity check:
    # keep the record if we at least got metadata or one real metric
    has_any_metric = any(
        v is not None for k, v in base.items()
        if k not in {"name", "sector", "industry", "country", "currency", "website", "ticker"}
    )

    has_identity = base["name"] != ticker or info.get("symbol") or info.get("shortName") or info.get("longName")

    if not has_any_metric and not has_identity:
        return {}

    return base


def fetch_multiple(tickers: Union[str, Iterable], verbose: bool = True) -> dict:
    """
    Fetch data for multiple tickers.
    Accepts either:
    - comma-separated string: "AAPL, MSFT, TSLA"
    - iterable: ["AAPL", "MSFT", "TSLA"]

    Returns:
        {ticker: metrics_dict}
    """
    ticker_list = _normalize_tickers(tickers)
    results = {}

    for ticker in ticker_list:
        if verbose:
            print(f"Fetching {ticker}...")
        data = fetch_company_data(ticker)
        if data:
            results[ticker] = data

    return results


def metrics_to_dataframe(results: dict) -> pd.DataFrame:
    """Convert nested results dict to a flat DataFrame."""
    if not results:
        return pd.DataFrame()

    rows = []
    metadata_keys = {"name", "sector", "industry", "country", "currency", "website", "ticker"}

    for ticker, metrics in results.items():
        row = {
            "ticker": ticker,
            "name": metrics.get("name"),
            "sector": metrics.get("sector"),
            "industry": metrics.get("industry"),
            "country": metrics.get("country"),
            "currency": metrics.get("currency"),
            "website": metrics.get("website"),
        }

        for key, value in metrics.items():
            if key not in metadata_keys:
                row[key] = value

        rows.append(row)

    return pd.DataFrame(rows)
