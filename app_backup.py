# app.py
import sqlite3
import streamlit as st
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from config import DB_PATH, RISK_FREE_RATE, BENCHMARK_TICKER
from src import (
    compute_cagr, compute_volatility, compute_sharpe, 
    compute_sortino, compute_max_drawdown, compute_beta, 
    compute_var_historical, compute_drawdown_series
)

st.set_page_config(page_title="NSE Risk-Adjusted Screener", layout="wide")
st.title("NSE Risk-Adjusted Screener")
st.caption(f"**Benchmark: {BENCHMARK_TICKER} (Nifty 50) | Risk-Free Rate ($R_f$): {RISK_FREE_RATE*100:.1f}% (India 10Y G-Sec yield)**")

# 1. Load Data from SQLite
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT ticker, date, daily_return FROM stock_prices ORDER BY date ASC", conn)
    conn.close()
    return df

data = load_data()

# Separate Benchmark & Equities
bench_series = data[data["ticker"] == BENCHMARK_TICKER].set_index("date")["daily_return"]
stocks_df = data[data["ticker"] != BENCHMARK_TICKER]
pivot_returns = stocks_df.pivot(index="date", columns="ticker", values="daily_return")

# Align common trading dates between equities and benchmark
common_dates = pivot_returns.index.intersection(bench_series.index)
pivot_returns = pivot_returns.loc[common_dates]
bench_series = bench_series.loc[common_dates]

# 2. Time Horizon Selector
horizon_choice = st.radio("Select Lookback Window", ["1 Year", "3 Years", "5 Years"], horizontal=True)
trading_days = {"1 Year": 252, "3 Years": 252 * 3, "5 Years": 252 * 5}[horizon_choice]

# Slice both with identical date windows
sub_returns = pivot_returns.tail(trading_days)
sub_bench = bench_series.loc[sub_returns.index]

# 3. Compute Real-time Scorecard
summary = []
for ticker in sub_returns.columns:
    r = sub_returns[ticker].dropna()
    if len(r) < 30:
        continue
    summary.append({
        "Ticker": ticker,
        "CAGR": compute_cagr(r),
        "Volatility": compute_volatility(r),
        "Sharpe": compute_sharpe(r, RISK_FREE_RATE),
        "Sortino": compute_sortino(r, RISK_FREE_RATE),
        "Max Drawdown": compute_max_drawdown(r),
        "Beta": compute_beta(r, sub_bench),
        "1D 95% VaR": compute_var_historical(r)
    })

scorecard_df = pd.DataFrame(summary).sort_values("Sharpe", ascending=False).reset_index(drop=True)
scorecard_df.index += 1

# Display Leaderboard
st.subheader("Risk-Adjusted Ranking Leaderboard")
st.dataframe(
    scorecard_df.style.format({
        "CAGR": "{:.2%}", "Volatility": "{:.2%}", "Sharpe": "{:.2f}",
        "Sortino": "{:.2f}", "Max Drawdown": "{:.2%}", "Beta": "{:.2f}", "1D 95% VaR": "{:.2%}"
    }),
    width='stretch'
)

# 4. Head-to-Head Comparison & Drawdown Chart
st.subheader("Head-to-Head Comparison")
valid_tickers = sub_returns.columns.tolist()
default_selection = [t for t in ["TCS.NS", "TATAMOTORS.NS"] if t in valid_tickers]

if len(default_selection) < 2:
    default_selection = valid_tickers[:2]

selected = st.multiselect(
    "Select 2 to 4 stocks to compare", 
    valid_tickers, 
    default=default_selection,
    max_selections=4
)

if len(selected) >= 2:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("**Core Metrics Comparison**")
        comp_metrics = scorecard_df[scorecard_df["Ticker"].isin(selected)].set_index("Ticker")
        display_metrics = comp_metrics[["CAGR", "Sharpe", "Sortino", "Max Drawdown", "Beta"]].T
        st.dataframe(
            display_metrics.style.format({
                col: "{:.2%}" if metric in ["CAGR", "Max Drawdown"] else "{:.2f}"
                for col in display_metrics.columns
                for metric in display_metrics.index
            }),
            width="stretch"
        )
    
    with col2:
        st.markdown("**Historical Drawdown (%)**")
        fig, ax = plt.subplots(figsize=(8, 4.5))
        for t in selected:
            dd = compute_drawdown_series(sub_returns[t]) * 100
            ax.plot(pd.to_datetime(dd.index), dd, label=t, linewidth=1.5)
        ax.set_ylabel("Drawdown %")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()
        st.pyplot(fig)

    # 5. Correlation Heatmap
    st.subheader("Portfolio Diversification Check")
    fig_corr, ax_corr = plt.subplots(figsize=(5, 3))
    sns.heatmap(
        sub_returns[selected].corr(),
        annot=True, 
        fmt=".2f",
        cmap="coolwarm", 
        vmin=-0.2, 
        vmax=1.0, 
        cbar_kws={"shrink": 0.8},
        annot_kws={"size": 7},
        ax=ax_corr
    )
    ax_corr.tick_params(labelsize=6)
    cbar = ax_corr.collections[0].colorbar
    cbar.ax.tick_params(labelsize=7)
    st.pyplot(fig_corr)

else:
    st.info("Please select at least 2 stocks to inspect comparative risk metrics and correlation.")