# 📊 StockRiskAdjustedScreener
### Which stocks are actually worth the risk you're taking?

🔗 **Live Dashboard:** [your-streamlit-link-here]
💻 **Code:** You're already here

---

## 🎯 The Problem

Retail investors pick stocks based on raw returns alone — "this stock gave 40% 
this year" — without adjusting for how much risk they took to get there. 
Two stocks can post identical returns while one is a rollercoaster and the 
other is steady. Free tools like Yahoo Finance and stock screeners show 
return numbers but not risk-adjusted performance, so investors routinely 
mispriced risk and chase volatile winners.

## 💡 The Solution

A screener that pulls 5 years of historical price data for [20] NSE-listed 
stocks, cleans it, and ranks them using the same risk-adjusted metrics used 
in professional quant/portfolio analysis — not just raw return.

**Metrics computed:**
- **Sharpe Ratio** — return per unit of total risk
- **Sortino Ratio** — return per unit of downside risk only
- **Maximum Drawdown** — worst peak-to-trough loss an investor would've endured
- **Beta** — sensitivity to Nifty50 market movements (via OLS regression)
- **Value at Risk (95%)** — the loss threshold you'd breach only 5% of the time
- **Correlation matrix** — checks if a "diversified" portfolio is actually diversified

## 🔑 Key Insights

*(fill these in once you run the analysis — always use real numbers)*
- [Stock X] had the [2nd] highest raw return but the [worst] Sortino ratio 
  in the dataset, meaning most of its gains came bundled with high downside risk
- [Stock Y] and [Stock Z] looked like diversified picks but showed a [0.85] 
  correlation — holding both added minimal diversification benefit
- [X]% of high-return stocks in the sample carried a Beta above 1.5, 
  meaning they amplify market downturns

## 🛠️ Tech Stack

**Data Engineering**
- Python, yfinance API — data collection
- Pandas — cleaning, missing-date handling, return calculation
- SQLite — storage for cleaned historical data

**Data Analysis**
- NumPy, SciPy — Sharpe/Sortino/VaR calculations
- statsmodels — OLS regression for Beta
- Pandas — correlation analysis

**Visualization & Deployment**
- Matplotlib, Seaborn — drawdown curves, heatmaps
- Streamlit — interactive dashboard
- GitHub + Streamlit Community Cloud — free hosting

## 📐 Methodology

1. Pulled 5 years of daily OHLCV data for [20] stocks + Nifty50 benchmark
2. Cleaned missing trading days and verified adjusted close prices
3. Computed daily returns, then derived all risk metrics (annualized where applicable)
4. Built a composite scorecard ranking stocks across all 6 metrics
5. Deployed an interactive dashboard for live stock comparison

## 📸 Screenshot

![dashboard screenshot](link-to-screenshot.png)

## 🚀 How to Run Locally

```bash
git clone [your-repo-link]
pip install -r requirements.txt
streamlit run app.py
```

## 📈 Future Scope

- Portfolio optimization using Markowitz Efficient Frontier
- Backtesting a simple risk-adjusted trading strategy
- Extending to NASDAQ/S&P500 stocks for cross-market comparison

## 👤 About Me

[Your name] | [LinkedIn] | [Email]
Aspiring Data Analyst with a data engineering foundation — built this to 
apply real portfolio-risk math to a problem I actually care about as a retail investor.