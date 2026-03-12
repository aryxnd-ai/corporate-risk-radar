"""
Corporate Health Score Model
=============================
Weighted multi-factor scoring model based on fundamental financial analysis.
Methodology inspired by Altman Z-Score, Piotroski F-Score, and modern
credit risk frameworks used in institutional finance.
"""

from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class HealthScoreResult:
    total_score: float
    grade: str
    components: dict
    interpretation: str
    percentile_estimate: float


HEALTH_WEIGHTS = {
    "profitability": 0.30,
    "growth": 0.25,
    "leverage": 0.20,
    "efficiency": 0.15,
    "liquidity": 0.10,
}


def _score_profitability(
    profit_margin: Optional[float],
    roa: Optional[float],
    roe: Optional[float],
) -> float:
    score = 0.0
    count = 0

    if profit_margin is not None:
        if profit_margin > 0.25:
            score += 100
        elif profit_margin > 0.15:
            score += 80
        elif profit_margin > 0.08:
            score += 60
        elif profit_margin > 0.02:
            score += 40
        elif profit_margin > 0:
            score += 20
        else:
            score += 0
        count += 1

    if roa is not None:
        if roa > 0.20:
            score += 100
        elif roa > 0.12:
            score += 80
        elif roa > 0.06:
            score += 60
        elif roa > 0.02:
            score += 40
        elif roa > 0:
            score += 20
        else:
            score += 0
        count += 1

    if roe is not None:
        if roe > 0.30:
            score += 100
        elif roe > 0.20:
            score += 80
        elif roe > 0.12:
            score += 60
        elif roe > 0.05:
            score += 40
        elif roe > 0:
            score += 20
        else:
            score += 0
        count += 1

    return score / max(count, 1)


def _score_growth(
    revenue_growth: Optional[float],
    earnings_growth: Optional[float],
) -> float:
    score = 0.0
    count = 0

    if revenue_growth is not None:
        if revenue_growth > 0.30:
            score += 100
        elif revenue_growth > 0.15:
            score += 85
        elif revenue_growth > 0.05:
            score += 65
        elif revenue_growth > 0:
            score += 45
        elif revenue_growth > -0.05:
            score += 25
        else:
            score += 5
        count += 1

    if earnings_growth is not None:
        if earnings_growth > 0.30:
            score += 100
        elif earnings_growth > 0.15:
            score += 82
        elif earnings_growth > 0.05:
            score += 62
        elif earnings_growth > 0:
            score += 42
        elif earnings_growth > -0.10:
            score += 22
        else:
            score += 5
        count += 1

    return score / max(count, 1)


def _score_leverage(
    debt_to_equity: Optional[float],
    debt_to_ebitda: Optional[float],
) -> float:
    score = 0.0
    count = 0

    if debt_to_equity is not None:
        d2e = abs(debt_to_equity)
        if d2e < 30:
            score += 100
        elif d2e < 80:
            score += 80
        elif d2e < 150:
            score += 60
        elif d2e < 250:
            score += 35
        elif d2e < 400:
            score += 15
        else:
            score += 5
        count += 1

    if debt_to_ebitda is not None:
        if debt_to_ebitda < 1:
            score += 100
        elif debt_to_ebitda < 2:
            score += 80
        elif debt_to_ebitda < 3:
            score += 60
        elif debt_to_ebitda < 5:
            score += 35
        elif debt_to_ebitda < 8:
            score += 15
        else:
            score += 5
        count += 1

    return score / max(count, 1)


def _score_efficiency(
    asset_turnover: Optional[float],
    operating_cf_ratio: Optional[float],
) -> float:
    score = 0.0
    count = 0

    if asset_turnover is not None:
        if asset_turnover > 1.0:
            score += 100
        elif asset_turnover > 0.7:
            score += 80
        elif asset_turnover > 0.4:
            score += 60
        elif asset_turnover > 0.2:
            score += 40
        else:
            score += 20
        count += 1

    if operating_cf_ratio is not None:
        if operating_cf_ratio > 0.25:
            score += 100
        elif operating_cf_ratio > 0.15:
            score += 80
        elif operating_cf_ratio > 0.05:
            score += 60
        elif operating_cf_ratio > 0:
            score += 35
        else:
            score += 5
        count += 1

    return score / max(count, 1)


def _score_liquidity(
    current_ratio: Optional[float],
    quick_ratio: Optional[float],
) -> float:
    score = 0.0
    count = 0

    if current_ratio is not None:
        if 1.5 <= current_ratio <= 3.0:
            score += 100
        elif 1.2 <= current_ratio < 1.5:
            score += 75
        elif 1.0 <= current_ratio < 1.2:
            score += 55
        elif current_ratio >= 3.0:
            score += 70
        else:
            score += 15
        count += 1

    if quick_ratio is not None:
        if quick_ratio >= 1.0:
            score += 100
        elif quick_ratio >= 0.7:
            score += 70
        elif quick_ratio >= 0.5:
            score += 45
        else:
            score += 20
        count += 1

    return score / max(count, 1)


def _grade(score: float) -> str:
    if score >= 85:
        return "A+"
    elif score >= 78:
        return "A"
    elif score >= 70:
        return "A-"
    elif score >= 62:
        return "B+"
    elif score >= 55:
        return "B"
    elif score >= 47:
        return "B-"
    elif score >= 38:
        return "C+"
    elif score >= 30:
        return "C"
    elif score >= 20:
        return "D"
    else:
        return "F"


def _interpret(score: float) -> str:
    if score >= 78:
        return "Financially robust. Strong fundamentals with low distress probability."
    elif score >= 62:
        return "Solid financial position. Some areas for improvement but broadly healthy."
    elif score >= 47:
        return "Moderate financial health. Monitor key metrics for deterioration."
    elif score >= 30:
        return "Financial stress signals present. Elevated risk of continued underperformance."
    else:
        return "Significant financial distress. High probability of ongoing operational challenges."


def calculate_health_score(metrics: dict) -> HealthScoreResult:
    """
    Calculate composite health score from financial metrics dictionary.
    Returns a HealthScoreResult with component breakdown.
    """
    prof = _score_profitability(
        metrics.get("profitMargins"),
        metrics.get("returnOnAssets"),
        metrics.get("returnOnEquity"),
    )
    growth = _score_growth(
        metrics.get("revenueGrowth"),
        metrics.get("earningsGrowth"),
    )
    lev = _score_leverage(
        metrics.get("debtToEquity"),
        metrics.get("debtToEbitda"),
    )
    eff = _score_efficiency(
        metrics.get("assetTurnover"),
        metrics.get("operatingCashflowRatio"),
    )
    liq = _score_liquidity(
        metrics.get("currentRatio"),
        metrics.get("quickRatio"),
    )

    total = (
        prof * HEALTH_WEIGHTS["profitability"] +
        growth * HEALTH_WEIGHTS["growth"] +
        lev * HEALTH_WEIGHTS["leverage"] +
        eff * HEALTH_WEIGHTS["efficiency"] +
        liq * HEALTH_WEIGHTS["liquidity"]
    )

    percentile = float(np.clip(total, 0, 100))

    return HealthScoreResult(
        total_score=round(total, 1),
        grade=_grade(total),
        components={
            "Profitability": round(prof, 1),
            "Growth": round(growth, 1),
            "Leverage": round(lev, 1),
            "Efficiency": round(eff, 1),
            "Liquidity": round(liq, 1),
        },
        interpretation=_interpret(total),
        percentile_estimate=round(percentile, 1),
    )
