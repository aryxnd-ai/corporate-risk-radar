# 📡 Corporate Health & Risk Radar

> **A professional financial analytics platform for evaluating corporate financial health and detecting early distress signals — built for economists, fintech engineers, and quantitative analysts.**

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue?style=flat-square&logo=python)](https://python.org)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-FF4B4B?style=flat-square&logo=streamlit)](https://streamlit.io)
[![Data](https://img.shields.io/badge/data-Yahoo%20Finance-purple?style=flat-square)](https://finance.yahoo.com)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

## 🎯 Overview

Corporate Health & Risk Radar is an end-to-end financial intelligence tool that pulls live data from Yahoo Finance, runs it through a multi-factor economic scoring model, and surfaces early warning signals — all accessible through a Bloomberg-inspired terminal dashboard.

It is designed to demonstrate skills in:

- **Quantitative financial modeling** (health scoring, risk detection)
- **Economic methodology** (Altman Z-Score, Piotroski F-Score, Beneish M-Score)
- **Data engineering** (data ingestion, normalization, derived metric computation)
- **Full-stack fintech development** (Python backend + Streamlit dashboard)
- **Portfolio analytics** (multi-company comparison, quadrant analysis)

---

## 🖥️ Dashboard Preview

The dashboard features a dark terminal aesthetic inspired by professional trading platforms:

- 🔵 **Single Company Deep-Dive** — gauge chart, radar chart, risk signal breakdown, Altman Z-Score
- 🟡 **Portfolio Screener** — multi-company health ranking, risk heatmap, quadrant scatter, exportable scorecard
- ⬇️ **CSV Export** — download all results for further analysis

---

## 📐 Economic Methodology

### Health Score Model

A 5-factor weighted composite (0–100 scale) inspired by institutional credit analysis:

| Factor | Weight | Metrics Used |
|---|---|---|
| **Profitability** | 30% | Net Margin, ROA, ROE |
| **Growth** | 25% | Revenue Growth, Earnings Growth |
| **Leverage** | 20% | Debt/Equity, Debt/EBITDA |
| **Efficiency** | 15% | Asset Turnover, Operating CF Margin |
| **Liquidity** | 10% | Current Ratio, Quick Ratio |

**Grade Scale:** A+ (≥85) · A (≥78) · A- (≥70) · B+ (≥62) · B (≥55) · B- (≥47) · C+ (≥38) · C (≥30) · D (≥20) · F (<20)

### Risk Radar — 8 Early Warning Signals

Each signal is independently evaluated and binary-triggered:

| Signal | Trigger Condition | Methodology Basis |
|---|---|---|
| Revenue Decline | YoY growth < -3% | Leading distress indicator |
| Margin Compression | Operating margin < 5% | Pre-default pattern detection |
| Excessive Leverage | D/E > 200% | Credit risk threshold |
| Liquidity Risk | Current ratio < 1.0x | Short-term solvency |
| Asset Inefficiency | ROA < 2% | Capital deployment failure |
| Earnings Quality | Accrual ratio > 10% | Beneish M-Score (inspired) |
| Market Volatility Exposure | Beta > 1.5 | Systematic risk amplification |
| Dual Growth Contraction | Revenue & Earnings both negative | Altman Z-Score precursor |

### Altman Z-Score Proxy

An approximation of the classic Altman Z-Score (1968) using available yfinance metrics:

```
Z ≈ 1.2×(Working Capital/Assets) + 3.3×(ROA) + 0.6×(Equity/Debt proxy) + 1.0×(Asset Turnover)
```

| Z-Score | Zone |
|---|---|
| > 2.99 | 🟢 Safe Zone — low bankruptcy probability |
| 1.81 – 2.99 | 🟡 Grey Zone — monitoring required |
| < 1.81 | 🔴 Distress Zone — elevated default risk |

---

## 🗂️ Repository Structure

```
corporate-risk-radar/
│
├── src/                        # Core Python package
│   ├── models/
│   │   ├── health_score.py     # 5-factor health scoring model
│   │   └── risk_radar.py       # 8-signal early warning system
│   ├── utils/
│   │   └── data_fetcher.py     # Yahoo Finance data ingestion layer
│   └── run_analysis.py         # CLI runner (terminal output)
│
├── dashboard/
│   └── app.py                  # Streamlit web dashboard
│
├── tests/
│   └── test_models.py          # Unit tests (pytest)
│
├── notebooks/                  # Jupyter notebooks for exploration
├── data/                       # Raw and processed data cache
├── docs/                       # Documentation and screenshots
│
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/corporate-risk-radar.git
cd corporate-risk-radar
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3a. Run the CLI analyzer

```bash
cd src

# Analyze default watchlist (AAPL, MSFT, TSLA, NVDA, META, AMZN, GOOGL, JPM)
python run_analysis.py

# Analyze specific companies
python run_analysis.py AAPL TSLA NVDA

# Export results to CSV
python run_analysis.py AAPL TSLA MSFT --export results.csv
```

**Example CLI output:**

```
╔══════════════════════════════════════════════════════════╗
║     CORPORATE HEALTH & RISK RADAR  ·  Financial Intel    ║
╚══════════════════════════════════════════════════════════╝

  Fetching 3 companies…

  ┌─ AAPL — Apple Inc.
  │  Sector: Technology
  │
  │  HEALTH SCORE  A  82/100  [████████████████░░░░]
  │  Financially robust. Strong fundamentals with low distress probability.
  │
  │    Profitability     91.2  [██████████]
  │    Growth            68.5  [██████░░░░]
  │    Leverage          72.0  [███████░░░]
  │    Efficiency        85.0  [████████░░]
  │    Liquidity         55.0  [█████░░░░░]
  │
  │  RISK RADAR  LOW  (1 signal active)
  │    ▲ [MEDIUM  ] Earnings Quality Risk
  │              Accrual ratio of 12.3% — reported earnings significantly outpace...
  │
  │  Altman Z-Score (proxy): 3.45 — SAFE ZONE
  │
  │  Key Metrics:
  │    Rev Growth:  +15.7%   Net Margin: +27.0%   D/E: 103%   ROA: +24.4%
  └──────────────────────────────────────────────────────────

  ── PORTFOLIO SUMMARY ─────────────────────────────────────
  Ticker   Company                Health   Grade    Risk    Signals
  ──────── ────────────────────── ──────── ──────── ──────────────
  AAPL     Apple Inc.               82      A        LOW        1
  MSFT     Microsoft Corp.          85      A+       MINIMAL    0
  TSLA     Tesla Inc.               34      D        ELEVATED   4
```

### 3b. Launch the web dashboard

```bash
streamlit run dashboard/app.py
```

Then open **http://localhost:8501** in your browser.

### 4. Run tests

```bash
pytest tests/ -v
```

---

## 📊 Example Analysis — S&P 500 Mega-Caps

| Company | Health Score | Grade | Risk Level | Key Risk |
|---|---|---|---|---|
| Microsoft (MSFT) | ~85 | A+ | MINIMAL | None |
| Apple (AAPL) | ~82 | A | LOW | Earnings quality |
| NVIDIA (NVDA) | ~78 | A- | LOW | Beta exposure |
| Meta (META) | ~72 | A- | LOW | Leverage |
| Amazon (AMZN) | ~64 | B+ | MODERATE | Margin compression |
| Alphabet (GOOGL) | ~76 | A- | LOW | None |
| Tesla (TSLA) | ~34 | D | ELEVATED | Revenue, margins, dual contraction |

*Values approximate — run the tool for live data.*

---

## 🛠️ Technical Stack

| Layer | Technology |
|---|---|
| Data Ingestion | `yfinance` — Yahoo Finance API wrapper |
| Numerical Modeling | `numpy`, `pandas` |
| Web Dashboard | `Streamlit` |
| Visualization | `Plotly` (gauges, radar charts, scatter, bar) |
| Testing | `pytest` |

---

## 📚 Academic & Methodological References

- **Altman, E.I. (1968)** — *Financial Ratios, Discriminant Analysis and the Prediction of Corporate Bankruptcy*. Journal of Finance.
- **Piotroski, J.D. (2000)** — *Value Investing: The Use of Historical Financial Statement Information to Separate Winners from Losers*. Journal of Accounting Research.
- **Beneish, M.D. (1999)** — *The Detection of Earnings Manipulation*. Financial Analysts Journal.
- **Beaver, W.H. (1966)** — *Financial Ratios as Predictors of Failure*. Journal of Accounting Research.

---

## ⚠️ Disclaimer

This tool is built for **educational and portfolio demonstration purposes only**. It does not constitute financial advice. All data is sourced from Yahoo Finance and may be delayed or inaccurate. Always consult qualified financial professionals before making investment decisions.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
