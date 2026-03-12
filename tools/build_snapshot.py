"""
Build local snapshot for portfolio screener
Run locally:
python3 tools/build_snapshot.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import time
import pandas as pd

from utils.data_fetcher import fetch_company_data
from models.health_score import calculate_health_score
from models.risk_radar import calculate_risk_score


TICKERS = [
    "AAPL", "MSFT", "NVDA", "AMZN", "META", "GOOGL", "NFLX", "AMD", "ORCL", "ADBE",
    "JPM", "BAC", "GS", "MS", "C", "WFC", "V", "MA", "COF", "PYPL",
    "COST", "WMT", "TGT", "MCD", "SBUX", "NKE", "KO", "PEP", "PG", "DIS",
    "UNH", "JNJ", "LLY", "ABBV", "MRK", "PFE", "TMO", "DHR", "ISRG", "MDT",
    "XOM", "CVX", "CAT", "GE", "HON", "DE", "ETN", "BA", "RTX", "UPS"
]


def main():
    rows = []

    for i, ticker in enumerate(TICKERS, start=1):
        print(f"[{i}/{len(TICKERS)}] Fetching {ticker}...")
        metrics = fetch_company_data(ticker)

        if not metrics:
            print(f"  -> skipped {ticker}")
            continue

        try:
            health = calculate_health_score(metrics)
            risk = calculate_risk_score(metrics)

            rows.append({
                "ticker": ticker,
                "name": metrics.get("name", ticker),
                "sector": metrics.get("sector", "Unknown"),
                "industry": metrics.get("industry", "Unknown"),
                "health_score": health.total_score,
                "grade": health.grade,
                "risk_score": risk.risk_score,
                "risk_level": risk.risk_level,
                "altman_z": risk.altman_z_proxy,
                "rev_growth": metrics.get("revenueGrowth"),
                "earnings_growth": metrics.get("earningsGrowth"),
                "net_margin": metrics.get("profitMargins"),
                "roa": metrics.get("returnOnAssets"),
                "roe": metrics.get("returnOnEquity"),
                "d2e": metrics.get("debtToEquity"),
                "current_ratio": metrics.get("currentRatio"),
                "quick_ratio": metrics.get("quickRatio"),
                "beta": metrics.get("beta"),
                "asset_turnover": metrics.get("assetTurnover"),
                "op_cf_ratio": metrics.get("operatingCashflowRatio"),
                "debt_to_ebitda": metrics.get("debtToEbitda"),
                "profitability_component": health.components.get("Profitability"),
                "growth_component": health.components.get("Growth"),
                "leverage_component": health.components.get("Leverage"),
                "efficiency_component": health.components.get("Efficiency"),
                "liquidity_component": health.components.get("Liquidity"),
                "health_interpretation": health.interpretation,
                "risk_summary": risk.summary,
            })
        except Exception as e:
            print(f"  -> failed scoring {ticker}: {e}")

        time.sleep(1.5)

    df = pd.DataFrame(rows).sort_values("health_score", ascending=False)
    outdir = Path(__file__).parent.parent / "data"
    outdir.mkdir(exist_ok=True)
    outfile = outdir / "portfolio_snapshot.csv"
    df.to_csv(outfile, index=False)

    print(f"\nSaved {len(df)} rows to {outfile}")


if __name__ == "__main__":
    main()
