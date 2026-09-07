## Phase 1: Foundation 
**Step 1 — Environment**
- Open Google Colab, create a notebook: `stock_risk_screener.ipynb`
- Install: `!pip install yfinance pandas numpy scipy statsmodels matplotlib seaborn`

**Step 2 — Pick your universe**
- Pick 15-20 stocks you'll track (mix of sectors: IT, banking, FMCG, auto — e.g., `TCS.NS, INFY.NS, HDFCBANK.NS, RELIANCE.NS, ITC.NS...`)
- Pick 1 benchmark index: `^NSEI` (Nifty50)
- Write these as a Python list — this is your config, keep it at the top of the notebook

**Step 3 — Pull raw data**
- Use `yfinance.download()` to pull 5 years of daily OHLCV data for all tickers + benchmark
- Just print `.head()` and `.tail()` for each — confirm data actually came through
- **Milestone check:** you should see a DataFrame with Open/High/Low/Close/Volume per stock

## Phase 2: Data Engineering (Day 3-4) — your 30%
**Step 4 — Clean it**
- Check for missing dates (holidays vs actual gaps), forward-fill or drop as appropriate
- Check for stock splits/bonus adjustments — yfinance's `Close` is usually already adjusted, but verify by spot-checking one known split event
- Handle any tickers that failed to download (delisted/wrong symbol) — log them, don't silently drop

**Step 5 — Structure it**
- Convert to daily returns: `df['returns'] = df['Close'].pct_change()`
- Store cleaned data into SQLite (`sqlite3` library, one table per ticker or one long-format table with a `ticker` column — long format is better for analysis later)
- **Milestone check:** you have a queryable database file, not just a notebook variable

## Phase 3: The Core Analysis (Day 5-8) — your 70%, do these ONE AT A TIME
**Step 6 — Sharpe Ratio** (start here, it's the simplest)
- Formula: `(mean daily return - risk-free rate) / std of daily returns`, annualized by `* sqrt(252)`
- Use India's ~7% T-bill rate as risk-free rate (or 0 for simplicity first)
- Rank all 15-20 stocks by Sharpe → print a sorted table
- **This alone is already a mini-project you could show someone.**

**Step 7 — Sortino Ratio**
- Same as Sharpe but denominator = std of only *negative* returns
- Compare: does the Sharpe ranking change under Sortino? Note which stocks look "safer" under Sortino — write this observation down, it becomes an insight later

**Step 8 — Max Drawdown**
- Compute cumulative returns → running max → drawdown = (current - running max) / running max
- Plot drawdown curves for top 3 stocks — this is your first real visual

**Step 9 — Beta (regression)**
- Use `statsmodels.OLS`: regress each stock's daily returns against Nifty50's daily returns
- Beta = the slope coefficient
- Flag stocks with Beta > 1.5 (aggressive) vs < 0.7 (defensive)

**Step 10 — Value at Risk (VaR)**
- Start with historical method (simplest): 5th percentile of the historical returns distribution
- `np.percentile(returns, 5)` → that's your 95% VaR
- Interpret it in words: "5% chance of losing more than X% in a day"

## Phase 4: Synthesis (Day 9-10)
**Step 11 — Build the composite scorecard**
- One table: Ticker | Return | Sharpe | Sortino | Max Drawdown | Beta | VaR
- This is the actual "product" — sort/filter it multiple ways and write down 3-4 genuine findings (e.g., "Stock X had the 2nd highest return but the worst Sortino, meaning most of its gains came with high downside risk")

**Step 12 — Correlation heatmap (bonus)**
- Correlation matrix of returns across your 15-20 stocks → Seaborn heatmap
- Talking point: "these 3 stocks look diversified but are 0.85 correlated — not real diversification"

## Phase 5: Make it visible (Day 11-13)
**Step 13 — Streamlit dashboard**
- Move logic from notebook into a `.py` script
- Build: ticker selector → shows Sharpe/Sortino/VaR/Beta + drawdown chart for chosen stock(s)
- Deploy on Streamlit Community Cloud (free, connects directly to your GitHub repo)

**Step 14 — GitHub + README**
- Push everything to GitHub
- README structure: Problem → Solution → Tech Stack → Live Demo link → Key Insights (with numbers) → Screenshot
- This README is what recruiters actually read — spend real time on it

---

**Don't skip before moving to the next, Debugging one metric at a time is 10x easier than debugging five at once.

StockRiskAdjustedScreener/
├── .github/
│   └── workflows/
│       └── daily_pipeline.yml     # Nightly automated data sync
├── config/
│   └── settings.py               # Risk-free rate, ticker list, database URIs
├── data/                         # Local SQLite fallback storage
│   └── screener.db
├── src/
│   ├── __init__.py
│   ├── db.py                     # SQLAlchemy models and engine setup
│   ├── pipeline.py               # Extraction, cleaning, and database upsert
│   └── metrics.py                # Pure NumPy/Pandas/SciPy quant formulas
├── tests/
│   └── test_metrics.py           # Unit tests validating mathematical output
├── app.py                        # Interactive Streamlit dashboard
├── requirements.txt
└── README.md

---
### Summary of the project

t analyzes a stock's 5-year track record and calculates whether the returns justify the associated risk, rather than evaluating performance based on nominal price gains alone.

#### How It Delivers the Verdict
Instead of providing a generic buy or sell recommendation, the screener categorizes a stock by its risk-adjusted profile:

"Worth It" (High Quality Compounder): The stock generated strong returns with shallow drawdowns and low downside volatility (High Sharpe & Sortino, low Max Drawdown).

"Not Worth It" (High-Risk Trap): The stock showed impressive top-line gains, but required enduring severe crashes, high downside swings, and outsized market sensitivity along the way.

"Defensive Preserver": Returns were modest, but the asset acted as a portfolio stabilizer during broader market downturns (Low Beta, minimal Drawdown).