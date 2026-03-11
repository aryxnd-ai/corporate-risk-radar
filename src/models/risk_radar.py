"""
Risk Radar Model
=================
Multi-signal early warning system for corporate financial distress.
Inspired by academic research on leading indicators of corporate default,
earnings manipulation detection (Beneish M-Score), and macro-stress frameworks.

Each signal is independently evaluated; the aggregate produces a risk profile
rather than a single scalar — giving analysts richer information.
"""

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class RiskSignal:
    name: str
    triggered: bool
    severity: str          # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    description: str
    metric_value: Optional[float] = None
    threshold: Optional[float] = None


@dataclass
class RiskRadarResult:
    risk_score: int            # 0–10 signal count
    risk_level: str            # MINIMAL / LOW / MODERATE / ELEVATED / HIGH / CRITICAL
    signals: List[RiskSignal]
    summary: str
    altman_z_proxy: Optional[float] = None


# ── Individual Signal Detectors ────────────────────────────────────────────────

def _sig_revenue_decline(revenue_growth: Optional[float]) -> RiskSignal:
    if revenue_growth is None:
        return RiskSignal("Revenue Decline", False, "LOW", "Revenue growth data unavailable.")
    triggered = revenue_growth < -0.03
    severity  = "HIGH" if revenue_growth < -0.10 else ("MEDIUM" if triggered else "LOW")
    return RiskSignal(
        name="Revenue Decline",
        triggered=triggered,
        severity=severity,
        description=f"Revenue contracted {abs(revenue_growth)*100:.1f}% YoY — potential demand destruction or market share loss." if triggered
                    else f"Revenue growth of {revenue_growth*100:.1f}% YoY — no contraction signal.",
        metric_value=revenue_growth,
        threshold=-0.03,
    )


def _sig_margin_compression(profit_margin: Optional[float], operating_margin: Optional[float]) -> RiskSignal:
    val = operating_margin if operating_margin is not None else profit_margin
    if val is None:
        return RiskSignal("Margin Compression", False, "LOW", "Margin data unavailable.")
    triggered = val < 0.05
    severity  = "CRITICAL" if val < 0 else ("HIGH" if val < 0.02 else ("MEDIUM" if triggered else "LOW"))
    return RiskSignal(
        name="Margin Compression",
        triggered=triggered,
        severity=severity,
        description=f"{'Operating' if operating_margin else 'Net'} margin of {val*100:.1f}% — below healthy threshold." if triggered
                    else f"Margins at {val*100:.1f}% — adequate profitability cushion.",
        metric_value=val,
        threshold=0.05,
    )


def _sig_high_leverage(debt_to_equity: Optional[float]) -> RiskSignal:
    if debt_to_equity is None:
        return RiskSignal("Excessive Leverage", False, "LOW", "Debt-to-equity data unavailable.")
    d2e = abs(debt_to_equity)
    triggered = d2e > 200
    severity  = "CRITICAL" if d2e > 500 else ("HIGH" if d2e > 300 else ("MEDIUM" if triggered else "LOW"))
    return RiskSignal(
        name="Excessive Leverage",
        triggered=triggered,
        severity=severity,
        description=f"D/E ratio of {d2e:.0f}% signals high financial leverage and debt-service risk." if triggered
                    else f"D/E ratio of {d2e:.0f}% — leverage within manageable range.",
        metric_value=d2e,
        threshold=200,
    )


def _sig_liquidity_crunch(current_ratio: Optional[float], quick_ratio: Optional[float]) -> RiskSignal:
    val = current_ratio
    if val is None:
        return RiskSignal("Liquidity Risk", False, "LOW", "Current ratio data unavailable.")
    triggered = val < 1.0
    severity  = "CRITICAL" if val < 0.5 else ("HIGH" if val < 0.75 else ("MEDIUM" if triggered else "LOW"))
    return RiskSignal(
        name="Liquidity Risk",
        triggered=triggered,
        severity=severity,
        description=f"Current ratio of {val:.2f}x — liabilities exceed short-term assets, cash flow risk elevated." if triggered
                    else f"Current ratio of {val:.2f}x — adequate short-term liquidity.",
        metric_value=val,
        threshold=1.0,
    )


def _sig_negative_roa(roa: Optional[float]) -> RiskSignal:
    if roa is None:
        return RiskSignal("Asset Inefficiency", False, "LOW", "ROA data unavailable.")
    triggered = roa < 0.02
    severity  = "HIGH" if roa < 0 else ("MEDIUM" if triggered else "LOW")
    return RiskSignal(
        name="Asset Inefficiency",
        triggered=triggered,
        severity=severity,
        description=f"ROA of {roa*100:.2f}% — assets generating insufficient returns." if triggered
                    else f"ROA of {roa*100:.2f}% — assets deployed effectively.",
        metric_value=roa,
        threshold=0.02,
    )


def _sig_earnings_quality(operating_cf_ratio: Optional[float], profit_margin: Optional[float]) -> RiskSignal:
    """Cash earnings vs accrual earnings divergence — Beneish M-Score inspired."""
    if operating_cf_ratio is None or profit_margin is None:
        return RiskSignal("Earnings Quality", False, "LOW", "Cash flow data unavailable.")
    divergence = profit_margin - operating_cf_ratio
    triggered  = divergence > 0.10  # Large accrual component
    severity   = "HIGH" if divergence > 0.20 else ("MEDIUM" if triggered else "LOW")
    return RiskSignal(
        name="Earnings Quality Risk",
        triggered=triggered,
        severity=severity,
        description=f"Accrual ratio of {divergence*100:.1f}% — reported earnings significantly outpace cash generation. Potential earnings management." if triggered
                    else f"Accrual ratio of {divergence*100:.1f}% — earnings quality appears sound.",
        metric_value=divergence,
        threshold=0.10,
    )


def _sig_volatility(beta: Optional[float]) -> RiskSignal:
    if beta is None:
        return RiskSignal("Market Volatility Exposure", False, "LOW", "Beta data unavailable.")
    triggered = beta > 1.5
    severity  = "HIGH" if beta > 2.5 else ("MEDIUM" if triggered else "LOW")
    return RiskSignal(
        name="Market Volatility Exposure",
        triggered=triggered,
        severity=severity,
        description=f"Beta of {beta:.2f} — stock price highly sensitive to market swings, amplified drawdown risk." if triggered
                    else f"Beta of {beta:.2f} — market sensitivity within normal range.",
        metric_value=beta,
        threshold=1.5,
    )


def _sig_negative_growth_momentum(revenue_growth: Optional[float], earnings_growth: Optional[float]) -> RiskSignal:
    """Both top-line and bottom-line contracting simultaneously."""
    if revenue_growth is None or earnings_growth is None:
        return RiskSignal("Dual Growth Contraction", False, "LOW", "Growth data incomplete.")
    triggered = revenue_growth < 0 and earnings_growth < 0
    severity  = "HIGH" if (revenue_growth < -0.05 and earnings_growth < -0.10) else ("MEDIUM" if triggered else "LOW")
    return RiskSignal(
        name="Dual Growth Contraction",
        triggered=triggered,
        severity=severity,
        description=f"Both revenue ({revenue_growth*100:.1f}%) and earnings ({earnings_growth*100:.1f}%) contracting — classic pre-distress pattern." if triggered
                    else "Revenue and earnings trends do not show simultaneous contraction.",
        metric_value=min(revenue_growth, earnings_growth),
        threshold=0,
    )


# ── Altman Z-Score Proxy ───────────────────────────────────────────────────────

def _altman_z_proxy(
    working_capital_ratio: Optional[float],
    roa: Optional[float],
    debt_to_equity: Optional[float],
    asset_turnover: Optional[float],
) -> Optional[float]:
    """
    Simplified Z-Score proxy using available yfinance metrics.
    Original Altman Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 1.0*X5
    Interpretation: >2.99 Safe, 1.81–2.99 Grey Zone, <1.81 Distress
    """
    if None in (working_capital_ratio, roa, debt_to_equity, asset_turnover):
        return None

    x1 = working_capital_ratio if working_capital_ratio else 0
    x3 = roa if roa else 0
    x4 = 1 / (abs(debt_to_equity) / 100 + 0.01)  # inverse D/E proxy for equity/debt
    x5 = asset_turnover if asset_turnover else 0

    z = 1.2 * x1 + 3.3 * x3 + 0.6 * x4 + 1.0 * x5
    return round(z, 2)


# ── Risk Level Mapping ─────────────────────────────────────────────────────────

def _risk_level(score: int, has_critical: bool) -> str:
    if has_critical:        return "CRITICAL"
    if score == 0:          return "MINIMAL"
    elif score <= 1:        return "LOW"
    elif score <= 3:        return "MODERATE"
    elif score <= 5:        return "ELEVATED"
    else:                   return "HIGH"


def _summarize(level: str, score: int, signals: list) -> str:
    triggered = [s.name for s in signals if s.triggered]
    if not triggered:
        return "No material risk signals detected. Company displays strong financial characteristics."
    top = triggered[:3]
    return (
        f"{score} risk signal{'s' if score != 1 else ''} detected ({level} risk). "
        f"Primary concerns: {', '.join(top)}."
    )


# ── Public API ─────────────────────────────────────────────────────────────────

def calculate_risk_score(metrics: dict) -> RiskRadarResult:
    signals = [
        _sig_revenue_decline(metrics.get("revenueGrowth")),
        _sig_margin_compression(metrics.get("profitMargins"), metrics.get("operatingMargins")),
        _sig_high_leverage(metrics.get("debtToEquity")),
        _sig_liquidity_crunch(metrics.get("currentRatio"), metrics.get("quickRatio")),
        _sig_negative_roa(metrics.get("returnOnAssets")),
        _sig_earnings_quality(metrics.get("operatingCashflowRatio"), metrics.get("profitMargins")),
        _sig_volatility(metrics.get("beta")),
        _sig_negative_growth_momentum(metrics.get("revenueGrowth"), metrics.get("earningsGrowth")),
    ]

    triggered_signals = [s for s in signals if s.triggered]
    score       = len(triggered_signals)
    has_critical = any(s.severity == "CRITICAL" for s in triggered_signals)
    level       = _risk_level(score, has_critical)

    z_score = _altman_z_proxy(
        metrics.get("workingCapitalRatio"),
        metrics.get("returnOnAssets"),
        metrics.get("debtToEquity"),
        metrics.get("assetTurnover"),
    )

    return RiskRadarResult(
        risk_score=score,
        risk_level=level,
        signals=signals,
        summary=_summarize(level, score, triggered_signals),
        altman_z_proxy=z_score,
    )
