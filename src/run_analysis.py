"""
Corporate Health & Risk Radar — CLI Runner
==========================================
Analyze one or more companies and display a formatted terminal report.

Usage:
    python run_analysis.py                        # analyzes default watchlist
    python run_analysis.py AAPL TSLA NVDA         # analyzes specified tickers
    python run_analysis.py --export results.csv   # export to CSV
"""

import sys
import argparse
import json
from datetime import datetime
from pathlib import Path

# Make src importable when running from any directory
sys.path.insert(0, str(Path(__file__).parent))

from utils.data_fetcher import fetch_multiple
from models.health_score import calculate_health_score
from models.risk_radar import calculate_risk_score

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_WATCHLIST = ["AAPL", "MSFT", "TSLA", "NVDA", "META", "AMZN", "GOOGL", "JPM"]

RISK_COLORS = {
    "MINIMAL":  "\033[92m",   # bright green
    "LOW":      "\033[32m",   # green
    "MODERATE": "\033[33m",   # yellow
    "ELEVATED": "\033[91m",   # light red
    "HIGH":     "\033[31m",   # red
    "CRITICAL": "\033[95m",   # magenta
}
GRADE_COLORS = {
    "A+": "\033[92m", "A": "\033[92m", "A-": "\033[32m",
    "B+": "\033[32m", "B": "\033[33m", "B-": "\033[33m",
    "C+": "\033[91m", "C": "\033[91m", "D":  "\033[31m", "F": "\033[31m",
}
RESET = "\033[0m"
BOLD  = "\033[1m"
DIM   = "\033[2m"


# ── Formatting Helpers ────────────────────────────────────────────────────────

def _color(text, code): return f"{code}{text}{RESET}"
def _fmt_pct(v):        return f"{v*100:+.1f}%" if v is not None else "N/A"
def _fmt_float(v, d=2): return f"{v:.{d}f}" if v is not None else "N/A"
def _bar(score, width=20):
    filled = int(score / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _print_header():
    print()
    print(_color("╔══════════════════════════════════════════════════════════╗", BOLD))
    print(_color("║     CORPORATE HEALTH & RISK RADAR  ·  Financial Intel    ║", BOLD))
    print(_color("╚══════════════════════════════════════════════════════════╝", BOLD))
    print(_color(f"  Analysis run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", DIM))
    print()


def _print_company(ticker, metrics, health, risk):
    name    = metrics.get("name", ticker)
    sector  = metrics.get("sector", "Unknown")
    grade_c = GRADE_COLORS.get(health.grade, "")
    risk_c  = RISK_COLORS.get(risk.risk_level, "")

    print(_color(f"  ┌─ {ticker} — {name}", BOLD))
    print(f"  │  Sector: {sector}")
    print()

    # Health Score bar
    bar = _bar(health.total_score)
    print(f"  │  HEALTH SCORE  {_color(health.grade, grade_c + BOLD)}  "
          f"{_color(f'{health.total_score:.0f}/100', grade_c)}  [{bar}]")
    print(f"  │  {DIM}{health.interpretation}{RESET}")
    print()

    # Component breakdown
    for comp, val in health.components.items():
        mini_bar = _bar(val, width=10)
        print(f"  │    {comp:<16} {val:>5.1f}  [{mini_bar}]")
    print()

    # Risk signals
    triggered = [s for s in risk.signals if s.triggered]
    print(f"  │  RISK RADAR  {_color(risk.risk_level, risk_c + BOLD)}  "
          f"({risk.risk_score} signal{'s' if risk.risk_score != 1 else ''} active)")
    if triggered:
        for s in triggered:
            sev_c = {"LOW": "\033[33m", "MEDIUM": "\033[91m", "HIGH": "\033[31m", "CRITICAL": "\033[95m"}.get(s.severity, "")
            print(f"  │    {_color('▲', sev_c)} [{s.severity:<8}] {s.name}")
            print(f"  │              {DIM}{s.description}{RESET}")
    else:
        print(f"  │    {_color('✓', RISK_COLORS['MINIMAL'])} No risk signals triggered")

    if risk.altman_z_proxy is not None:
        z = risk.altman_z_proxy
        z_label = "SAFE ZONE" if z > 2.99 else ("GREY ZONE" if z > 1.81 else "DISTRESS ZONE")
        z_c = "\033[32m" if z > 2.99 else ("\033[33m" if z > 1.81 else "\033[31m")
        print(f"  │")
        print(f"  │  Altman Z-Score (proxy): {_color(f'{z:.2f}', z_c + BOLD)} — {_color(z_label, z_c)}")

    # Key metrics row
    print(f"  │")
    print(f"  │  Key Metrics:")
    print(f"  │    Rev Growth:  {_fmt_pct(metrics.get('revenueGrowth'))}   "
          f"Net Margin: {_fmt_pct(metrics.get('profitMargins'))}   "
          f"D/E: {_fmt_float(metrics.get('debtToEquity'), 0)}%   "
          f"ROA: {_fmt_pct(metrics.get('returnOnAssets'))}")
    print(f"  └{'─'*58}")
    print()


def _print_summary_table(results_list):
    """Print a compact comparison table across all companies."""
    print(_color("\n  ── PORTFOLIO SUMMARY ─────────────────────────────────────", BOLD))
    print(f"  {'Ticker':<8} {'Company':<22} {'Health':>8} {'Grade':>6} {'Risk':>10} {'Signals':>8}")
    print(f"  {'─'*8} {'─'*22} {'─'*8} {'─'*6} {'─'*10} {'─'*8}")

    for r in sorted(results_list, key=lambda x: x["health"].total_score, reverse=True):
        t      = r["ticker"]
        name   = r["metrics"].get("name", t)[:21]
        h      = r["health"]
        risk   = r["risk"]
        grade_c = GRADE_COLORS.get(h.grade, "")
        risk_c  = RISK_COLORS.get(risk.risk_level, "")
        print(
            f"  {t:<8} {name:<22} "
            f"{_color(f'{h.total_score:.0f}', grade_c):>18} "
            f"{_color(h.grade, grade_c):>16} "
            f"{_color(risk.risk_level, risk_c):>20} "
            f"{risk.risk_score:>8}"
        )
    print()


def _export_csv(results_list, path: str):
    import csv
    fieldnames = [
        "ticker", "name", "sector",
        "health_score", "grade",
        "profitability", "growth", "leverage", "efficiency", "liquidity",
        "risk_score", "risk_level", "altman_z",
        "revenueGrowth", "profitMargins", "debtToEquity", "returnOnAssets",
    ]
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in results_list:
            m = r["metrics"]
            h = r["health"]
            ri = r["risk"]
            w.writerow({
                "ticker":       r["ticker"],
                "name":         m.get("name", ""),
                "sector":       m.get("sector", ""),
                "health_score": h.total_score,
                "grade":        h.grade,
                "profitability": h.components["Profitability"],
                "growth":        h.components["Growth"],
                "leverage":      h.components["Leverage"],
                "efficiency":    h.components["Efficiency"],
                "liquidity":     h.components["Liquidity"],
                "risk_score":   ri.risk_score,
                "risk_level":   ri.risk_level,
                "altman_z":     ri.altman_z_proxy or "",
                "revenueGrowth":  m.get("revenueGrowth", ""),
                "profitMargins":  m.get("profitMargins", ""),
                "debtToEquity":   m.get("debtToEquity", ""),
                "returnOnAssets": m.get("returnOnAssets", ""),
            })
    print(f"  Exported to {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Corporate Health & Risk Radar CLI")
    parser.add_argument("tickers", nargs="*", help="Ticker symbols to analyze (default: built-in watchlist)")
    parser.add_argument("--export", metavar="FILE", help="Export results to CSV")
    parser.add_argument("--json", metavar="FILE", help="Export results to JSON")
    args = parser.parse_args()

    tickers  = [t.upper() for t in args.tickers] if args.tickers else DEFAULT_WATCHLIST

    _print_header()
    print(f"  Fetching data for {len(tickers)} companies…\n")

    raw = fetch_multiple(tickers, verbose=True)
    print()

    results_list = []
    for ticker, metrics in raw.items():
        health = calculate_health_score(metrics)
        risk   = calculate_risk_score(metrics)
        _print_company(ticker, metrics, health, risk)
        results_list.append({"ticker": ticker, "metrics": metrics, "health": health, "risk": risk})

    _print_summary_table(results_list)

    if args.export:
        _export_csv(results_list, args.export)

    if args.json:
        out = []
        for r in results_list:
            out.append({
                "ticker":      r["ticker"],
                "name":        r["metrics"].get("name", ""),
                "health":      {"score": r["health"].total_score, "grade": r["health"].grade, "components": r["health"].components},
                "risk":        {"score": r["risk"].risk_score, "level": r["risk"].risk_level},
            })
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"  JSON exported to {args.json}")


if __name__ == "__main__":
    main()
