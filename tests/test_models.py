"""
Unit tests for Health Score and Risk Radar models.
Run with: pytest tests/
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from models.health_score import calculate_health_score, HealthScoreResult
from models.risk_radar import calculate_risk_score, RiskRadarResult


# ── Fixture Data ───────────────────────────────────────────────────────────────

HEALTHY_COMPANY = {
    "profitMargins":    0.28,
    "returnOnAssets":   0.22,
    "returnOnEquity":   0.35,
    "revenueGrowth":    0.18,
    "earningsGrowth":   0.20,
    "debtToEquity":     50.0,
    "currentRatio":     2.0,
    "quickRatio":       1.5,
    "assetTurnover":    0.8,
    "operatingCashflowRatio": 0.22,
    "beta":             1.1,
    "operatingMargins": 0.30,
}

DISTRESSED_COMPANY = {
    "profitMargins":    -0.05,
    "returnOnAssets":   -0.02,
    "returnOnEquity":   -0.08,
    "revenueGrowth":    -0.12,
    "earningsGrowth":   -0.20,
    "debtToEquity":     450.0,
    "currentRatio":     0.6,
    "quickRatio":       0.3,
    "assetTurnover":    0.2,
    "operatingCashflowRatio": -0.03,
    "beta":             2.8,
    "operatingMargins": -0.08,
}

NEUTRAL_COMPANY = {
    "profitMargins":    0.07,
    "returnOnAssets":   0.05,
    "revenueGrowth":    0.03,
    "debtToEquity":     140.0,
    "currentRatio":     1.3,
    "beta":             1.3,
}


# ── Health Score Tests ─────────────────────────────────────────────────────────

class TestHealthScore:
    def test_healthy_company_high_score(self):
        result = calculate_health_score(HEALTHY_COMPANY)
        assert isinstance(result, HealthScoreResult)
        assert result.total_score >= 70, f"Expected score >= 70, got {result.total_score}"

    def test_distressed_company_low_score(self):
        result = calculate_health_score(DISTRESSED_COMPANY)
        assert result.total_score <= 30, f"Expected score <= 30, got {result.total_score}"

    def test_score_bounded_0_100(self):
        for metrics in [HEALTHY_COMPANY, DISTRESSED_COMPANY, NEUTRAL_COMPANY, {}]:
            result = calculate_health_score(metrics)
            assert 0 <= result.total_score <= 100

    def test_grade_assigned(self):
        result = calculate_health_score(HEALTHY_COMPANY)
        assert result.grade in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F")

    def test_components_present(self):
        result = calculate_health_score(HEALTHY_COMPANY)
        for key in ("Profitability", "Growth", "Leverage", "Efficiency", "Liquidity"):
            assert key in result.components

    def test_components_bounded(self):
        result = calculate_health_score(HEALTHY_COMPANY)
        for k, v in result.components.items():
            assert 0 <= v <= 100, f"Component {k} out of range: {v}"

    def test_empty_metrics_returns_result(self):
        result = calculate_health_score({})
        assert isinstance(result, HealthScoreResult)

    def test_healthy_grade_is_A_range(self):
        result = calculate_health_score(HEALTHY_COMPANY)
        assert result.grade.startswith("A") or result.grade.startswith("B"), result.grade

    def test_distressed_grade_is_D_or_F(self):
        result = calculate_health_score(DISTRESSED_COMPANY)
        assert result.grade in ("D", "F", "C"), result.grade

    def test_ordering_healthy_beats_distressed(self):
        h = calculate_health_score(HEALTHY_COMPANY).total_score
        d = calculate_health_score(DISTRESSED_COMPANY).total_score
        assert h > d


# ── Risk Radar Tests ───────────────────────────────────────────────────────────

class TestRiskRadar:
    def test_distressed_triggers_multiple_signals(self):
        result = calculate_risk_score(DISTRESSED_COMPANY)
        assert result.risk_score >= 4, f"Expected >= 4 signals, got {result.risk_score}"

    def test_healthy_triggers_few_signals(self):
        result = calculate_risk_score(HEALTHY_COMPANY)
        assert result.risk_score <= 2, f"Expected <= 2 signals, got {result.risk_score}"

    def test_risk_level_assigned(self):
        result = calculate_risk_score(DISTRESSED_COMPANY)
        assert result.risk_level in ("MINIMAL", "LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL")

    def test_all_signals_present(self):
        result = calculate_risk_score(HEALTHY_COMPANY)
        assert len(result.signals) == 8

    def test_signals_have_required_fields(self):
        result = calculate_risk_score(HEALTHY_COMPANY)
        for sig in result.signals:
            assert sig.name
            assert sig.severity in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
            assert isinstance(sig.triggered, bool)

    def test_distressed_risk_level_high(self):
        result = calculate_risk_score(DISTRESSED_COMPANY)
        assert result.risk_level in ("ELEVATED", "HIGH", "CRITICAL")

    def test_healthy_risk_level_low(self):
        result = calculate_risk_score(HEALTHY_COMPANY)
        assert result.risk_level in ("MINIMAL", "LOW", "MODERATE")

    def test_empty_metrics_no_crash(self):
        result = calculate_risk_score({})
        assert isinstance(result, RiskRadarResult)

    def test_summary_is_string(self):
        result = calculate_risk_score(HEALTHY_COMPANY)
        assert isinstance(result.summary, str) and len(result.summary) > 0

    def test_revenue_decline_signal(self):
        metrics = {"revenueGrowth": -0.15}
        result  = calculate_risk_score(metrics)
        rev_sig = next(s for s in result.signals if s.name == "Revenue Decline")
        assert rev_sig.triggered is True

    def test_no_revenue_decline_signal(self):
        metrics = {"revenueGrowth": 0.20}
        result  = calculate_risk_score(metrics)
        rev_sig = next(s for s in result.signals if s.name == "Revenue Decline")
        assert rev_sig.triggered is False


if __name__ == "__main__":
    # Quick smoke test without pytest
    print("Running smoke tests…")
    t = TestHealthScore()
    t.test_healthy_company_high_score()
    t.test_distressed_company_low_score()
    t.test_score_bounded_0_100()
    t.test_ordering_healthy_beats_distressed()
    r = TestRiskRadar()
    r.test_distressed_triggers_multiple_signals()
    r.test_healthy_triggers_few_signals()
    r.test_revenue_decline_signal()
    print("All smoke tests passed ✓")
