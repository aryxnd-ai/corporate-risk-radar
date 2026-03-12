"""
Corporate Health & Risk Radar — Streamlit Dashboard
=====================================================
Run with:  streamlit run dashboard/app.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime

from utils.data_fetcher import fetch_company_data, fetch_multiple
from models.health_score import calculate_health_score
from models.risk_radar import calculate_risk_score

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Corporate Risk Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif;
    background: #0a0e1a;
    color: #c9d1e0;
  }

  .stApp { background: #0a0e1a; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #0d1220;
    border-right: 1px solid #1e2a45;
  }

  /* Cards */
  .metric-card {
    background: linear-gradient(135deg, #0f1729 0%, #111d33 100%);
    border: 1px solid #1e2a45;
    border-radius: 8px;
    padding: 20px;
    margin: 8px 0;
  }
  .metric-card-green  { border-left: 3px solid #00d084; }
  .metric-card-yellow { border-left: 3px solid #f5a623; }
  .metric-card-red    { border-left: 3px solid #e85d4a; }
  .metric-card-blue   { border-left: 3px solid #4a9eff; }

  .score-big {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 48px;
    font-weight: 600;
    letter-spacing: -2px;
  }
  .grade-badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 4px;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 600;
    font-size: 14px;
  }
  .risk-pill {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 1px;
    text-transform: uppercase;
  }
  .section-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #4a9eff;
    border-bottom: 1px solid #1e2a45;
    padding-bottom: 6px;
    margin: 24px 0 16px 0;
  }
  .signal-row {
    background: #0f1729;
    border: 1px solid #1e2a45;
    border-radius: 6px;
    padding: 12px 16px;
    margin: 6px 0;
  }
  .ticker-header {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 28px;
    font-weight: 600;
    color: #ffffff;
    letter-spacing: -1px;
  }
  .company-name {
    font-size: 14px;
    color: #6b7a99;
    margin-top: 2px;
  }
  .kpi-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #4a6080;
  }
  .kpi-value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 22px;
    font-weight: 600;
    color: #e0e8f5;
    margin-top: 2px;
  }
  .stButton > button {
    background: linear-gradient(135deg, #1a3a6b, #0f2244);
    color: #4a9eff;
    border: 1px solid #2a4a7a;
    border-radius: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    padding: 8px 20px;
    letter-spacing: 1px;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #1e4480, #132d5a);
    border-color: #4a9eff;
    color: #ffffff;
  }
  div[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Mono', monospace;
    color: #e0e8f5;
  }
  .streamlit-expanderHeader {
    background: #0f1729 !important;
    border: 1px solid #1e2a45 !important;
  }
</style>
""", unsafe_allow_html=True)

# ── Color helpers ──────────────────────────────────────────────────────────────

def health_color(score):
    if score >= 75:
        return "#00d084"
    if score >= 55:
        return "#4a9eff"
    if score >= 38:
        return "#f5a623"
    return "#e85d4a"


def risk_color(level):
    return {
        "MINIMAL": "#00d084",
        "LOW": "#4a9eff",
        "MODERATE": "#f5a623",
        "ELEVATED": "#e85d4a",
        "HIGH": "#e85d4a",
        "CRITICAL": "#c0392b",
    }.get(level, "#6b7a99")


def grade_color(grade):
    if grade in ("A+", "A", "A-"):
        return "#00d084"
    if grade in ("B+", "B", "B-"):
        return "#4a9eff"
    if grade in ("C+", "C"):
        return "#f5a623"
    return "#e85d4a"


def fmt_pct(v):
    if v is None:
        return "—"
    return f"{v*100:+.1f}%"


def fmt_float(v, d=2):
    if v is None:
        return "—"
    return f"{v:.{d}f}"


# ── Chart builders ─────────────────────────────────────────────────────────────

CHART_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(family="IBM Plex Mono, monospace", color="#8899bb", size=11),
    margin=dict(l=10, r=10, t=10, b=10),
)


def make_gauge(score, label="Health Score"):
    color = health_color(score)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": label, "font": {"size": 13, "color": "#6b7a99", "family": "IBM Plex Mono"}},
        number={"font": {"size": 36, "color": color, "family": "IBM Plex Mono"}, "suffix": ""},
        gauge={
            "axis": {
                "range": [0, 100],
                "tickcolor": "#1e2a45",
                "tickfont": {"size": 9, "family": "IBM Plex Mono"},
            },
            "bar": {"color": color, "thickness": 0.22},
            "bgcolor": "#0f1729",
            "bordercolor": "#1e2a45",
            "steps": [
                {"range": [0, 30], "color": "rgba(232,93,74,0.15)"},
                {"range": [30, 55], "color": "rgba(245,166,35,0.10)"},
                {"range": [55, 75], "color": "rgba(74,158,255,0.10)"},
                {"range": [75, 100], "color": "rgba(0,208,132,0.10)"},
            ],
            "threshold": {"line": {"color": color, "width": 2}, "value": score},
        },
    ))
    fig.update_layout(**CHART_LAYOUT, height=220)
    return fig


def make_radar(components: dict, ticker: str):
    cats = list(components.keys())
    vals = list(components.values())

    if not cats:
        cats = ["No Data"]
        vals = [0]

    cats_closed = cats + [cats[0]]
    vals_closed = vals + [vals[0]]

    color = health_color(sum(vals) / len(vals)) if vals else "#4a9eff"
    r = int(color[1:3], 16)
    g = int(color[3:5], 16)
    b = int(color[5:7], 16)

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=vals_closed,
        theta=cats_closed,
        fill="toself",
        fillcolor=f"rgba({r},{g},{b},0.15)",
        line=dict(color=color, width=2),
        name=ticker,
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=8, color="#4a6080"),
                gridcolor="#1e2a45",
                linecolor="#1e2a45",
            ),
            angularaxis=dict(
                tickfont=dict(size=10, color="#8899bb"),
                gridcolor="#1e2a45",
                linecolor="#1e2a45",
            ),
        ),
        showlegend=False,
        height=280,
    )
    return fig


def make_comparison_bar(df: pd.DataFrame):
    df_sorted = df.sort_values("health_score", ascending=True)
    colors = [health_color(s) for s in df_sorted["health_score"]]
    fig = go.Figure(go.Bar(
        x=df_sorted["health_score"],
        y=df_sorted["ticker"],
        orientation="h",
        marker=dict(color=colors, line=dict(width=0)),
        text=[f"{s:.0f}" for s in df_sorted["health_score"]],
        textfont=dict(family="IBM Plex Mono", size=11),
        textposition="outside",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        height=max(200, len(df_sorted) * 44),
        xaxis=dict(range=[0, 115], showgrid=False, zeroline=False, visible=False),
        yaxis=dict(showgrid=False, tickfont=dict(family="IBM Plex Mono", size=12, color="#c9d1e0")),
        bargap=0.35,
    )
    return fig


def make_risk_heatmap(df: pd.DataFrame):
    risk_order = {"MINIMAL": 0, "LOW": 1, "MODERATE": 2, "ELEVATED": 3, "HIGH": 4, "CRITICAL": 5}
    df_local = df.copy()
    df_local["risk_num"] = df_local["risk_level"].map(risk_order).fillna(2)
    df_sorted = df_local.sort_values("health_score", ascending=False)

    fig = go.Figure(go.Bar(
        x=df_sorted["ticker"],
        y=df_sorted["risk_score"],
        marker=dict(color=[risk_color(r) for r in df_sorted["risk_level"]], line=dict(width=0)),
        text=df_sorted["risk_level"],
        textfont=dict(family="IBM Plex Mono", size=9),
        textposition="outside",
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        height=260,
        yaxis=dict(
            title="Active Signals",
            showgrid=True,
            gridcolor="#1e2a45",
            tickfont=dict(family="IBM Plex Mono"),
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(family="IBM Plex Mono", size=12, color="#c9d1e0"),
        ),
    )
    return fig


def make_scatter_quadrant(df: pd.DataFrame):
    fig = go.Figure()

    fig.add_shape(type="rect", x0=0, y0=50, x1=5, y1=100, fillcolor="rgba(232,93,74,0.06)", line_width=0)
    fig.add_shape(type="rect", x0=0, y0=0, x1=5, y1=50, fillcolor="rgba(245,166,35,0.06)", line_width=0)
    fig.add_shape(type="rect", x0=5, y0=0, x1=10, y1=50, fillcolor="rgba(74,158,255,0.06)", line_width=0)
    fig.add_shape(type="rect", x0=5, y0=50, x1=10, y1=100, fillcolor="rgba(0,208,132,0.06)", line_width=0)

    fig.add_hline(y=50, line_dash="dot", line_color="#1e2a45", line_width=1)
    fig.add_vline(x=5, line_dash="dot", line_color="#1e2a45", line_width=1)

    colors = [health_color(s) for s in df["health_score"]]
    fig.add_trace(go.Scatter(
        x=df["risk_score"],
        y=df["health_score"],
        mode="markers+text",
        text=df["ticker"],
        textposition="top center",
        textfont=dict(family="IBM Plex Mono", size=11, color="#c9d1e0"),
        marker=dict(size=14, color=colors, line=dict(color="#0a0e1a", width=2)),
    ))
    fig.update_layout(
        **CHART_LAYOUT,
        height=320,
        xaxis=dict(
            title="Risk Signals",
            range=[-0.5, 9.5],
            showgrid=True,
            gridcolor="#1e2a45",
            tickfont=dict(family="IBM Plex Mono"),
        ),
        yaxis=dict(
            title="Health Score",
            range=[0, 105],
            showgrid=True,
            gridcolor="#1e2a45",
            tickfont=dict(family="IBM Plex Mono"),
        ),
    )

    annotations = [
        ("⚠ HIGH RISK / HEALTHY", 0.5, 97),
        ("⚠ HIGH RISK / DISTRESSED", 0.5, 5),
        ("✓ LOW RISK / HEALTHY", 7.5, 97),
        ("● LOW RISK / WEAK", 7.5, 5),
    ]
    for text, x, y in annotations:
        fig.add_annotation(
            x=x,
            y=y,
            text=text,
            font=dict(size=8, color="#2a3a55", family="IBM Plex Mono"),
            showarrow=False,
            xanchor="left",
        )
    return fig


# ── Session state ──────────────────────────────────────────────────────────────

if "portfolio" not in st.session_state:
    st.session_state.portfolio = {}

if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Single Company"

# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='font-family:IBM Plex Mono;font-size:13px;color:#4a9eff;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px'>
    📡 Risk Radar
    </div>
    <div style='font-size:11px;color:#4a6080;margin-bottom:20px'>Corporate Financial Intelligence</div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**SINGLE COMPANY ANALYSIS**")
    ticker_input = st.text_input(
        "Single company ticker",
        placeholder="e.g. AAPL, MSFT, TSLA",
        label_visibility="collapsed",
    ).upper().strip()
    run_single = st.button("▶  ANALYZE", width="stretch")

    st.markdown("---")
    st.markdown("**PORTFOLIO SCREENER**")

    company_presets = {
        "Custom": "AAPL, MSFT, TSLA, NVDA, META, AMZN, GOOGL, JPM, V, NFLX, AMD, COST",
        "Mega Cap Tech": "AAPL, MSFT, NVDA, AMZN, META, GOOGL, NFLX, AMD, ORCL, ADBE",
        "Banks & Payments": "JPM, BAC, GS, MS, C, WFC, V, MA, COF, PYPL",
        "Retail & Consumer": "COST, WMT, TGT, MCD, SBUX, NKE, KO, PEP, PG, DIS",
        "Healthcare": "UNH, JNJ, LLY, ABBV, MRK, PFE, TMO, DHR, ISRG, MDT",
        "Energy & Industrials": "XOM, CVX, CAT, GE, HON, DE, ETN, BA, RTX, UPS",
        "Balanced Market Leaders": "AAPL, MSFT, NVDA, AMZN, META, JPM, V, COST, UNH, XOM, CAT, KO",
    }

    preset_choice = st.selectbox(
        "Choose portfolio preset",
        list(company_presets.keys()),
        index=0,
    )

    default_list = company_presets[preset_choice]

    portfolio_input = st.text_area(
        "Portfolio tickers",
        value=default_list,
        height=140,
        label_visibility="collapsed",
    )

    run_portfolio = st.button("▶  RUN SCREENER", width="stretch")

    st.markdown("---")
    st.markdown("""
    <div style='font-size:10px;color:#2a3a55;font-family:IBM Plex Mono'>
    Data: Yahoo Finance · yfinance<br>
    Models: Weighted Multi-Factor<br>
    Altman Z-Score (proxy)<br>
    Beneish Earnings Quality<br>
    <br>
    ⚠ Not financial advice.
    </div>
    """, unsafe_allow_html=True)


# ── Single Company View ────────────────────────────────────────────────────────

if run_single and ticker_input:
    with st.spinner(f"Fetching {ticker_input}..."):
        metrics = fetch_company_data(ticker_input)

    if not metrics:
        st.error(f"Could not fetch data for '{ticker_input}'. Check the ticker symbol or try again in a minute.")
    else:
        health = calculate_health_score(metrics)
        risk = calculate_risk_score(metrics)
        name = metrics.get("name", ticker_input)
        sector = metrics.get("sector", "Unknown")

        hc = health_color(health.total_score)
        rc = risk_color(risk.risk_level)

        st.markdown(f"""
        <div class='metric-card'>
          <div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px'>
            <div>
              <div class='ticker-header'>{ticker_input}</div>
              <div class='company-name'>{name} · {sector}</div>
            </div>
            <div style='display:flex;gap:20px;align-items:center'>
              <div>
                <div class='kpi-label'>Health Score</div>
                <div class='kpi-value' style='color:{hc}'>{health.total_score:.0f} <span style='font-size:14px'>{health.grade}</span></div>
              </div>
              <div>
                <div class='kpi-label'>Risk Level</div>
                <div class='kpi-value' style='color:{rc}'>{risk.risk_level}</div>
              </div>
              <div>
                <div class='kpi-label'>Signals</div>
                <div class='kpi-value'>{risk.risk_score} / 8</div>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.plotly_chart(
                make_gauge(health.total_score),
                width="stretch",
                key=f"single_gauge_{ticker_input}",
            )
        with col2:
            st.plotly_chart(
                make_radar(health.components, ticker_input),
                width="stretch",
                key=f"single_radar_{ticker_input}",
            )

        st.markdown("<div class='section-header'>KEY FINANCIAL METRICS</div>", unsafe_allow_html=True)
        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Revenue Growth", fmt_pct(metrics.get("revenueGrowth")))
        m2.metric("Net Margin", fmt_pct(metrics.get("profitMargins")))
        m3.metric("ROA", fmt_pct(metrics.get("returnOnAssets")))
        m4.metric(
            "Debt / Equity",
            fmt_float(metrics.get("debtToEquity"), 0) + "%" if metrics.get("debtToEquity") is not None else "—",
        )
        m5.metric("Current Ratio", fmt_float(metrics.get("currentRatio")))
        m6.metric("Beta", fmt_float(metrics.get("beta")))

        st.markdown("<div class='section-header'>RISK SIGNAL BREAKDOWN</div>", unsafe_allow_html=True)
        sev_colors = {"LOW": "#f5a623", "MEDIUM": "#e87c3e", "HIGH": "#e85d4a", "CRITICAL": "#c0392b"}
        for sig in risk.signals:
            icon = "🔴" if sig.triggered else "🟢"
            sc = sev_colors.get(sig.severity, "#4a6080") if sig.triggered else "#2a4060"
            st.markdown(f"""
            <div class='signal-row' style='border-left:3px solid {sc}'>
              <div style='display:flex;justify-content:space-between;align-items:center'>
                <span style='font-family:IBM Plex Mono;font-size:13px;color:{"#e0e8f5" if sig.triggered else "#4a6080"}'>{icon} {sig.name}</span>
                {"<span style='font-size:10px;font-weight:600;color:" + sc + ";font-family:IBM Plex Mono;letter-spacing:1px'>" + sig.severity + "</span>" if sig.triggered else ""}
              </div>
              <div style='font-size:12px;color:#6b7a99;margin-top:4px'>{sig.description}</div>
            </div>
            """, unsafe_allow_html=True)

        if risk.altman_z_proxy is not None:
            z = risk.altman_z_proxy
            z_label = "SAFE ZONE (>2.99)" if z > 2.99 else ("GREY ZONE (1.81–2.99)" if z > 1.81 else "DISTRESS ZONE (<1.81)")
            z_c = "#00d084" if z > 2.99 else ("#f5a623" if z > 1.81 else "#e85d4a")
            st.markdown(f"""
            <div class='metric-card' style='margin-top:12px'>
              <div class='kpi-label'>ALTMAN Z-SCORE PROXY</div>
              <div style='display:flex;align-items:baseline;gap:16px;margin-top:6px'>
                <span style='font-family:IBM Plex Mono;font-size:32px;font-weight:600;color:{z_c}'>{z:.2f}</span>
                <span style='font-size:12px;color:{z_c};font-family:IBM Plex Mono'>{z_label}</span>
              </div>
              <div style='font-size:11px;color:#4a6080;margin-top:4px'>
                Proxy derived from available metrics. Original Altman Z interprets: >2.99 Safe · 1.81–2.99 Grey Zone · &lt;1.81 Distress
              </div>
            </div>
            """, unsafe_allow_html=True)

# ── Portfolio Screener View ────────────────────────────────────────────────────

elif run_portfolio and portfolio_input:
    tickers = [t.strip().upper() for t in portfolio_input.replace(",", " ").split() if t.strip()]

    with st.spinner(f"Fetching {len(tickers)} companies…"):
        raw = fetch_multiple(tickers, verbose=False)

    if not raw:
        st.error("No data could be fetched. Check your ticker list or try again in a minute.")
    else:
        rows = []
        for t, m in raw.items():
            h = calculate_health_score(m)
            ri = calculate_risk_score(m)
            rows.append({
                "ticker": t,
                "name": m.get("name", t)[:25],
                "sector": m.get("sector", "Unknown"),
                "health_score": h.total_score,
                "grade": h.grade,
                "risk_score": ri.risk_score,
                "risk_level": ri.risk_level,
                "altman_z": ri.altman_z_proxy,
                "rev_growth": m.get("revenueGrowth"),
                "net_margin": m.get("profitMargins"),
                "roa": m.get("returnOnAssets"),
                "d2e": m.get("debtToEquity"),
                "components": h.components,
                "metrics": m,
                "health": h,
                "risk": ri,
            })

        df = pd.DataFrame(rows)
        if df.empty:
            st.error("No valid companies were returned.")
        else:
            df_sorted = df.sort_values("health_score", ascending=False).reset_index(drop=True)

            st.markdown("<div class='section-header'>PORTFOLIO OVERVIEW</div>", unsafe_allow_html=True)
            ka, kb, kc, kd, ke = st.columns(5)
            ka.metric("Companies Analyzed", len(df))
            kb.metric("Avg Health Score", f"{df['health_score'].mean():.1f}")
            kc.metric("High Risk Companies", int((df["risk_level"].isin(["HIGH", "CRITICAL", "ELEVATED"])).sum()))
            kd.metric("Best Performer", df.loc[df["health_score"].idxmax(), "ticker"])
            ke.metric("Most Signals", df.loc[df["risk_score"].idxmax(), "ticker"])

            st.markdown("<div class='section-header'>HEALTH SCORE RANKING</div>", unsafe_allow_html=True)
            col_a, col_b = st.columns([3, 2])
            with col_a:
                st.plotly_chart(
                    make_comparison_bar(df_sorted),
                    width="stretch",
                    key="portfolio_comparison_bar",
                )
            with col_b:
                st.plotly_chart(
                    make_risk_heatmap(df_sorted),
                    width="stretch",
                    key="portfolio_risk_heatmap",
                )

            st.markdown("<div class='section-header'>RISK vs HEALTH QUADRANT</div>", unsafe_allow_html=True)
            st.plotly_chart(
                make_scatter_quadrant(df_sorted),
                width="stretch",
                key="portfolio_scatter_quadrant",
            )

            st.markdown("<div class='section-header'>COMPANY SCORECARD</div>", unsafe_allow_html=True)

            for i, row in df_sorted.iterrows():
                with st.expander(
                    f"{'🟢' if row['risk_score']==0 else '🟡' if row['risk_score']<=2 else '🔴'}  "
                    f"{row['ticker']}  ·  {row['name']}  ·  Health {row['health_score']:.0f}  ·  Risk {row['risk_level']}",
                    expanded=False,
                ):
                    c1, c2, c3 = st.columns([1, 1, 1])

                    with c1:
                        st.plotly_chart(
                            make_gauge(row["health_score"]),
                            width="stretch",
                            key=f"gauge_{row['ticker']}_{i}",
                        )

                    with c2:
                        st.plotly_chart(
                            make_radar(row["components"], row["ticker"]),
                            width="stretch",
                            key=f"radar_{row['ticker']}_{i}",
                        )

                    with c3:
                        st.markdown(f"""
                        <div style='padding:12px'>
                          <div class='kpi-label'>SECTOR</div>
                          <div style='color:#c9d1e0;font-size:14px;margin-bottom:12px'>{row.get("sector","—")}</div>
                          <div class='kpi-label'>INTERPRETATION</div>
                          <div style='color:#8899bb;font-size:12px;margin-bottom:12px'>{row["health"].interpretation}</div>
                          <div class='kpi-label'>RISK SUMMARY</div>
                          <div style='color:#8899bb;font-size:12px'>{row["risk"].summary}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    m1, m2, m3, m4 = st.columns(4)
                    m1.metric("Rev Growth", fmt_pct(row["rev_growth"]))
                    m2.metric("Net Margin", fmt_pct(row["net_margin"]))
                    m3.metric("ROA", fmt_pct(row["roa"]))
                    m4.metric(
                        "D/E Ratio",
                        fmt_float(row["d2e"], 0) + "%" if row["d2e"] is not None else "—",
                    )

            st.markdown("---")
            export_df = df_sorted[[
                "ticker", "name", "sector", "health_score", "grade",
                "risk_score", "risk_level", "altman_z",
                "rev_growth", "net_margin", "roa", "d2e"
            ]].copy()
            export_df.columns = [
                "Ticker", "Company", "Sector", "Health Score", "Grade",
                "Risk Signals", "Risk Level", "Altman Z (proxy)",
                "Revenue Growth", "Net Margin", "ROA", "D/E Ratio"
            ]
            csv = export_df.to_csv(index=False)
            st.download_button(
                "⬇  EXPORT RESULTS (CSV)",
                data=csv,
                file_name=f"risk_radar_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
            )

else:
    st.markdown("""
    <div style='text-align:center;padding:60px 0'>
      <div style='font-size:48px;margin-bottom:16px'>📡</div>
      <div style='font-family:IBM Plex Mono;font-size:20px;color:#4a9eff;margin-bottom:12px'>Ready to Analyze</div>
      <div style='color:#4a6080;font-size:14px;max-width:480px;margin:0 auto;line-height:1.7'>
        Enter a ticker in the sidebar for a deep single-company analysis,<br>
        or run the portfolio screener to compare multiple companies at once.
      </div>
      <div style='margin-top:40px;display:flex;justify-content:center;gap:32px;flex-wrap:wrap'>
        <div style='background:#0f1729;border:1px solid #1e2a45;border-radius:8px;padding:16px 24px;text-align:left;min-width:180px'>
          <div style='color:#4a9eff;font-family:IBM Plex Mono;font-size:11px;letter-spacing:1px'>HEALTH MODEL</div>
          <div style='color:#8899bb;font-size:12px;margin-top:6px'>5-factor weighted scoring<br>Profitability · Growth<br>Leverage · Efficiency<br>Liquidity</div>
        </div>
        <div style='background:#0f1729;border:1px solid #1e2a45;border-radius:8px;padding:16px 24px;text-align:left;min-width:180px'>
          <div style='color:#f5a623;font-family:IBM Plex Mono;font-size:11px;letter-spacing:1px'>RISK SIGNALS</div>
          <div style='color:#8899bb;font-size:12px;margin-top:6px'>8 early-warning signals<br>Revenue · Margins<br>Leverage · Liquidity<br>Earnings quality · Volatility</div>
        </div>
        <div style='background:#0f1729;border:1px solid #1e2a45;border-radius:8px;padding:16px 24px;text-align:left;min-width:180px'>
          <div style='color:#00d084;font-family:IBM Plex Mono;font-size:11px;letter-spacing:1px'>FRAMEWORKS</div>
          <div style='color:#8899bb;font-size:12px;margin-top:6px'>Altman Z-Score proxy<br>Beneish M-Score (inspired)<br>Piotroski F-Score (inspired)<br>Portfolio quadrant analysis</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
