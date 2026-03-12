"""
Financial Data Fetcher
========================
Rate-limit safer Yahoo Finance fetcher with caching, retries, and ticker parsing.
"""

from typing import Optional, Union, Iterable
import warnings
import time

import pandas as pd
import yfinance as yf
import streamlit as st

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


def _safe_float(val) -> Optional[float]:
    if val is None or val == "N/A":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _safe_get(data: dict, key: str) -> Optional[float]:
    if not isinstance(data, dict):
        return None
    return _safe_float(data.get(key))


def _clean_ticker(ticker: str) -> str:
    return str(ticker).strip().upper()


def _normalize_tickers(tickers: Union[str, Iterable]) -> list[str]:
    if tickers is None:
        return []

    if isinstance(tickers, str):
        raw = tickers.replace("\n", ",").split(",")
    else:
        raw = list(tickers)

    cleaned = []
    for t in raw:
        symbol = _clean_ticker(t)
        if symbol:
            cleaned.append(symbol)

    seen = set()
    unique = []
    for t in cleaned:
        if t not in seen:
            seen.add(t)
            unique.append(t)

    return unique


def _get_history_snapshot(ticker_obj) -> dict:
    out = {}
    try:
        hist = ticker_obj.history(period="5d", auto_adjust=False)
        if hist is not None and not hist.empty:
            if "Close" in hist:
                close_series = hist["Close"].dropna()
                if not close_series.empty:
                    out["lastClose"] = _safe_float(close_series.iloc[-1])
    except Exception:
        pass
    return out


def _get_fast_info_snapshot(ticker_obj) -> dict:
    out = {}
    try:
        fi = ticker_obj.fast_info
        if fi:
            out["marketCap"] = _safe_float(fi.get("market_cap"))
            out["currency"] = fi.get("currency")
            out["lastPrice"] = _safe_float(fi.get("last_price"))
            out["beta"] = _safe_float(fi.get("beta"))
    except Exception:
        pass
    return out


def _derive_metrics(base: dict) -> dict:
    derived = {}

    total_revenue = _safe_float(base.get("totalRevenue"))
    total_assets = _safe_float(base.get("totalAssets"))
    operating_cf = _safe_float(base.get("operatingCashflow"))
    current_assets = _safe_float(base.get("totalCurrentAssets"))
    current_liabilities = _safe_float(base.get("totalCurrentLiabilities"))
    total_debt = _safe_float(base.get("totalDebt"))
    ebitda = _safe_float(base.get("ebitda"))

    if total_revenue is not None and total_assets not in (None, 0):
        derived["assetTurnover"] = total_revenue / total_assets
    else:
        derived["assetTurnover"] = None

    if operating_cf is not None and total_revenue not in (None, 0):
        derived["operatingCashflowRatio"] = operating_cf / total_revenue
    else:
        derived["operatingCashflowRatio"] = None

    if (
        current_assets is not None
        and current_liabilities is not None
        and total_assets not in (None, 0)
    ):
        wc = current_assets - current_liabilities
        derived["workingCapitalRatio"] = wc / total_assets
    else:
        derived["workingCapitalRatio"] = None

    if total_debt is not None and ebitda not in (None, 0) and ebitda > 0:
        derived["debtToEbitda"] = total_debt / ebitda
    else:
        derived["debtToEbitda"] = None

    return derived


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_data(ticker: str, retries: int = 3, delay: float = 2.5) -> dict:
    """
    Cached single-ticker fetch. Cache is the main defense against rate limits.
    """
    ticker = _clean_ticker(ticker)
    if not ticker:
        return {}

    last_error = None

    for attempt in range(retries):
        try:
            t = yf.Ticker(ticker)

            info = {}
            try:
                info = t.info or {}
            except Exception as e:
                last_error = e
                info = {}

            fast = _get_fast_info_snapshot(t)
            hist = _get_history_snapshot(t)

            base = {key: _safe_get(info, key) for key in METRIC_KEYS}

            # extra fields used for derived metrics
            base["totalAssets"] = _safe_get(info, "totalAssets")
            base["totalCurrentAssets"] = _safe_get(info, "totalCurrentAssets")
            base["totalCurrentLiabilities"] = _safe_get(info, "totalCurrentLiabilities")

            # metadata
            base["name"] = (
                info.get("longName")
                or info.get("shortName")
                or info.get("displayName")
                or ticker
            )
            base["sector"] = info.get("sector") or "Unknown"
            base["industry"] = info.get("industry") or "Unknown"
            base["country"] = info.get("country") or "Unknown"
            base["currency"] = info.get("currency") or fast.get("currency") or "USD"
            base["website"] = info.get("website") or ""
            base["ticker"] = ticker

            # fallbacks
            if base.get("marketCap") is None:
                base["marketCap"] = fast.get("marketCap")
            if base.get("beta") is None:
                base["beta"] = fast.get("beta")
            if base.get("lastPrice") is None:
                base["lastPrice"] = fast.get("lastPrice")
            if base.get("lastClose") is None:
                base["lastClose"] = hist.get("lastClose")

            base.update(_derive_metrics(base))

            has_identity = (
                base["name"] != ticker
                or fast.get("lastPrice") is not None
                or hist.get("lastClose") is not None
                or bool(info)
            )

            has_any_metric = any(
                v is not None
                for k, v in base.items()
                if k not in {"name", "sector", "industry", "country", "currency", "website", "ticker"}
            )

            if has_identity or has_any_metric:
                return base

        except Exception as e:
            last_error = e

        if attempt < retries - 1:
            time.sleep(delay * (attempt + 1))

    print(f"[!] Failed to fetch {ticker}: {last_error}")
    return {}


def fetch_multiple(tickers: Union[str, Iterable], verbose: bool = True) -> dict:
    """
    Slower multi-fetch to reduce cloud-IP throttling.
    """
    ticker_list = _normalize_tickers(tickers)
    results = {}

    for i, ticker in enumerate(ticker_list):
        if verbose:
            print(f"Fetching {ticker}... ({i+1}/{len(ticker_list)})")

        data = fetch_company_data(ticker)
        if data:
            results[ticker] = data

        # slow spacing matters on Streamlit Cloud
        time.sleep(2.0)

    return results


def metrics_to_dataframe(results: dict) -> pd.DataFrame:
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
