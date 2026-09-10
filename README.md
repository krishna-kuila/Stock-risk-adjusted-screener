# Risk-Adjusted Stock Screener (Indian Equities)

🔗 **Live Demo:** [[Open App on Streamlit]](https://stock-risk-adjusted-screener.streamlit.app/)

An interactive stock analysis dashboard that helps you evaluate whether a stock's returns are actually worth the risk you take.

Most free screeners show raw past returns (like *"this stock gave 40% in a year"*), but they don't show how much price volatility or drawdown you had to sit through. This project pulls 5 years of daily price data and ranks Indian equities using portfolio-level metrics like Sharpe Ratio, Sortino Ratio, Maximum Drawdown, and Beta.

---

## 📌 Why I Built This

When retail investors look for stocks, they usually chase whatever went up the most recently. But two stocks with the same 20% annual return can have very different risk:
- One grows steadily with small 5–10% dips.
- The other crashes 35–40% before bouncing back, testing an investor's patience and leading to panic selling.

I built this screener to bring risk-adjusted evaluation into simple, practical terms for retail investors.

---

## 🚀 What the App Does

### 1. Pre-Loaded Universe + Live Custom Search
- **Nifty 50 Universe:** Comes pre-loaded with 5 years of daily data for 20 large-cap stocks across 7 sectors (IT, Banking, Auto, Energy, Pharma, FMCG, Materials), stored locally in SQLite for fast startup.
- **Search Any NSE Stock:** You can switch to "Custom Watchlist" and type any Indian stock symbol or name (e.g. `RIL`, `TCS`, `M&M`, `BAJAJ FINANCE`). A built-in alias resolver maps common name to their Yahoo Finance symbols and loads 5 years of daily returns in ~1.5 seconds.

### 2. Three Main Tabs
- **Tab 1: Screener & Rankings** — Displays a scorecard ranking stocks from best to worst by Sharpe Ratio. Filter by risk categories, set minimum CAGR thresholds, and export results to CSV.
- **Tab 2: Compare Stocks** — Pick 2 to 4 stocks and compare them side by side with:
  - Cumulative return growth chart
  - Drawdown curves from previous peaks
  - Correlation heatmap to check if your selected stocks actually provide diversification
- **Tab 3: Stock Deep Dive** — Inspect a single stock in detail:
  - 8-metric scorecard (CAGR, Volatility, Beta, Sharpe, Sortino, Max Drawdown, 1D 95% VaR, Risk Profile)
  - Plain-English verdict summarizing whether the stock's returns justified its risk
  - Market crash cushion (Downside Capture vs. Nifty 50 on red days)
  - Slump recovery time (how many days/months it took to recover from its worst drop)
  - 95% Historical Value-at-Risk (VaR) distribution

---

## 📊 Metrics Explained Simply

| Metric | What It Means | Why It Matters |
| :--- | :--- | :--- |
| **CAGR** | Compound Annual Growth Rate | The annualized return of the stock over the selected time period. |
| **Volatility** | Annual price swings | How wildly the stock price fluctuates each year. |
| **Sharpe Ratio** | Return earned above a safe 7.05% bank deposit per unit of total risk | Measures whether the extra return was worth the volatility. Above 1.0 is good; below 0 means it earned less than a safe fixed deposit. |
| **Sortino Ratio** | Return per unit of downside risk only | Focuses strictly on harmful drops, without penalizing sudden upside rallies. |
| **Max Drawdown** | Worst drop from top to bottom | The biggest percentage crash from a previous peak to the trough. |
| **Beta** | Sensitivity to Nifty 50 | Measures how fast the stock moves relative to the market (> 1.0 moves faster; < 1.0 is steadier). |
| **1D 95% VaR** | Value at Risk (95% confidence) | The maximum one-day loss expected on 95 out of 100 trading days. |
| **Downside Capture** | Performance on market down days | Shows what percentage of the Nifty's drop the stock absorbs when the market falls. |

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Visualizations:** Plotly (interactive charts with clean tooltips)
- **Data & Math:** Pandas, NumPy
- **Data Retrieval:** yfinance, curl_cffi (fast API queries with browser impersonation)
- **Database:** SQLite3 (stores pre-computed daily returns)
- **Package Management:** uv / pip

---

## 📁 Project Structure

```text
Stock_Risk_Adjusted_Screener/
├── app.py                      # Main Streamlit application
├── pyproject.toml              # Project dependencies and config
├── requirements.txt            # Clean pip requirements for deployment
├── .gitignore                  # Git ignore rules
│
├── .streamlit/
│   └── config.toml             # App theme configuration
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Global constants (risk-free rate, trading days)
│
├── data/
│   └── screener.db             # SQLite database storing historical returns
│
├── src/
│   ├── __init__.py
│   ├── fetcher.py              # Live stock fetcher with ticker alias resolution
│   ├── metrics.py              # Quantitative formulas (CAGR, Sharpe, Sortino, VaR, etc.)
│   ├── scoring.py              # Scorecard builder, categorizer, and table formatting
│   ├── charts.py               # Plotly chart builders
│   └── pipeline.py             # ETL script to refresh local database
│
└── tests/
    ├── test_live_precision.py  # Math precision unit tests
    └── test_tabs_integration.py# End-to-end integration tests
```

---

## 💻 Running Locally

### 1. Clone the repository
```bash
git clone https://github.com/krishna-kuila/Stock-risk-adjusted-screener.git

cd Stock-risk-adjusted-screener
```

### 2. Set up virtual environment & install dependencies
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt

0r 

uv sync
```

*(Alternatively, if you use `uv`: `uv run streamlit run app.py`)*

### 3. Run the application
```bash
streamlit run app.py
```

---

## 🧪 Testing

The repository includes **17 automated tests** verifying both the financial calculations and the UI integration:

```bash
python -m unittest discover tests -v
```

- **Unit tests:** Check CAGR, Volatility, Sharpe, Sortino, Max Drawdown peak-tracking, and 95% Historical VaR calculations against known test data.
- **Integration tests:** Test data slicing across 1-Year, 3-Year, and 5-Year horizons, single-stock watchlist handling, ticker alias resolution, and invalid ticker handling.

---
## Project Screenshots

![alt text](screenshots/Homepage.png)
![alt text](screenshots/rankings.png)
![alt text](screenshots/compare.png)![alt text](<screenshots/cumulative growth.png>)![alt text](screenshots/Drawdowns.png)![alt text](screenshots/correlation.png)![alt text](screenshots/deepdive.png)![alt text](screenshots/health_check.png)![alt text](screenshots/1dayloss.png)
