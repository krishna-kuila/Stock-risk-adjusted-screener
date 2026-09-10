import os
import sqlite3
import streamlit as st
import pandas as pd
import numpy as np

from config import DB_PATH, RISK_FREE_RATE, BENCHMARK_TICKER
from src import (
    compute_downside_capture, compute_upside_capture,
    compute_underwater_stats,
    fetch_stock_returns, build_scorecard, format_comparison_table,
    plot_cumulative_growth, plot_drawdown_curves,
    plot_correlation_matrix, plot_benchmark_comparison,
    plot_var_histogram
)

PLOTLY_CHART_CONFIG = {
    "scrollZoom": False,
    "displayModeBar": False,
    "doubleClick": False,
    "showAxisDragHandles": False,
}


def render_chart(fig):
    """Renders a Plotly chart with consistent container width and disabled toolbars."""
    st.plotly_chart(fig, width="stretch", theme=None, config=PLOTLY_CHART_CONFIG)


# ---------------------------------------------------------
# Page Configuration & Minimal Header
# ---------------------------------------------------------
st.set_page_config(page_title="Stock Risk-Adjusted Screener", page_icon="📈", layout="wide")

# Essential CSS Styling for Header and Chart Container
st.markdown("""
<style>
    .block-container,
    div[data-testid="stAppViewBlockContainer"],
    .stMainBlockContainer,
    section.main > div.block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2rem !important;
    }

    .header-container {
        padding-top: 4px !important;
        margin-top: 0 !important;
        padding-bottom: 4px;
        margin-bottom: 16px;
        text-align: center;
    }
    .main-title {
        margin: 0 !important;
        padding: 0 !important;
        font-size: 2.2rem;
        font-weight: 800;
        color: var(--text-color, #e4e4e7) !important;
        text-align: center;
        line-height: 1.2 !important;
    }
    .meta-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        justify-content: center;
        gap: 12px;
        margin-top: 14px;
    }
    .meta-item,
    .meta-pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.84rem;
        background-color: var(--secondary-background-color, #27272a) !important;
        border: 1px solid #3f3f46 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
    }
    .meta-label {
        font-weight: 600;
        color: #a1a1aa !important;
    }
    .meta-val,
    .tag-pill {
        display: inline-flex;
        align-items: center;
        font-weight: 700;
        color: var(--text-color, #e4e4e7) !important;
        background-color: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    /* Light Theme Adjustment */
    @media (prefers-color-scheme: light) {
        .meta-item,
        .meta-pill {
            background-color: #f4f4f5 !important;
            border-color: #e4e4e7 !important;
        }
        .meta-label {
            color: #71717a !important;
        }
        .meta-val,
        .tag-pill {
            color: #18181b !important;
        }
        .main-title {
            color: #18181b !important;
        }
    }

    /* Plotly Chart Container Border & Styling */
    div[data-testid="stPlotlyChart"] {
        border: 1px solid #3f3f46 !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        background-color: #27272a !important;
        margin-top: 6px !important;
        margin-bottom: 12px !important;
    }

    [data-testid="InputInstructions"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# 1. Load Data from SQLite
# ---------------------------------------------------------
@st.cache_data
def load_data(db_mtime: float = 0.0):
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT ticker, date, daily_return FROM stock_prices ORDER BY date ASC", conn)
    conn.close()
    return df

db_mtime = os.path.getmtime(DB_PATH) if os.path.exists(DB_PATH) else 0.0
data = load_data(db_mtime)

# Separate Benchmark & Equities
bench_series = data[data["ticker"] == BENCHMARK_TICKER].set_index("date")["daily_return"]
stocks_df = data[data["ticker"] != BENCHMARK_TICKER]
pivot_returns = stocks_df.pivot(index="date", columns="ticker", values="daily_return")

# Align common trading dates between equities and benchmark
common_dates = pivot_returns.index.intersection(bench_series.index)
pivot_returns = pivot_returns.loc[common_dates]
bench_series = bench_series.loc[common_dates]

# Real-time stock loader & benchmark loader (cached in-memory, zero database persistence)
@st.cache_data(show_spinner=False, ttl=3600)
def _cached_fetch_stock(ticker_sym: str):
    return fetch_stock_returns(ticker_sym, period="5y", valid_dates=None)


def load_realtime_stock(ticker_sym: str):
    """Fetches 5 years of daily returns on-demand with resilient caching and failure bypass."""
    res = _cached_fetch_stock(ticker_sym)
    if not res[0]:
        # If cached call was unsuccessful, retry with fresh fetch
        fresh = fetch_stock_returns(ticker_sym, period="5y", valid_dates=None)
        if fresh[0]:
            return fresh
    return res

load_realtime_stock.clear = _cached_fetch_stock.clear


@st.cache_data(show_spinner=False, ttl=3600)
def load_realtime_benchmark():
    """Fetches 5 years of daily returns for Nifty 50 benchmark (^NSEI) from Yahoo Finance in-memory."""
    ok, s, _ = fetch_stock_returns("^NSEI", period="5y", valid_dates=None)
    if ok and s is not None and not s.empty:
        return s
    return bench_series

# Clear all custom stocks and memory cache on fresh session / page reload
if "session_initialized" not in st.session_state:
    st.session_state.session_initialized = True
    st.session_state.custom_stocks = []
    load_realtime_stock.clear()
    load_realtime_benchmark.clear()

# ---------------------------------------------------------
# 2. Sidebar Controls & Stage Switcher
# ---------------------------------------------------------
st.sidebar.header("Controls")

# Toggle to switch between Preset Universe and Custom Watchlist
stage_toggle = st.sidebar.toggle(
    "Custom Watchlist", 
    value=True,
    help="Switch between Nifty 50 and your own stock list"
)

# Clean all custom stocks and cached data whenever the mode changes
if "prev_stage_toggle" not in st.session_state:
    st.session_state.prev_stage_toggle = stage_toggle

if st.session_state.prev_stage_toggle != stage_toggle:
    st.session_state.custom_stocks = []
    load_realtime_stock.clear()
    load_realtime_benchmark.clear()
    st.session_state.prev_stage_toggle = stage_toggle

if stage_toggle:
    st.sidebar.caption("Mode: **My Watchlist**")
else:
    st.sidebar.caption("Mode: **Nifty 50**")

st.sidebar.markdown("---")

horizon_choice = st.sidebar.radio("Period", ["1 Year", "3 Years", "5 Years"])
trading_days = {"1 Year": 252, "3 Years": 252 * 3, "5 Years": 252 * 5}[horizon_choice]

st.sidebar.markdown("---")
with st.sidebar.expander("Metric Definitions", expanded=True):
    st.markdown("""
    - **CAGR:** Average yearly profit earned by the stock.
    - **Volatility:** How much the price swings up and down each year.
    - **Sharpe Ratio:** Return earned per unit of risk (higher is better).
    - **Sortino Ratio:** Return vs. bad drops only (ignores upward jumps).
    - **Max Drawdown:** Biggest drop from peak to bottom (worst drop).
    - **Beta:** Movement vs. Nifty 50 (> 1.0 faster, < 1.0 steadier).
    - **1D 95% VaR:** Largest 1-day loss expected on 95 out of 100 days.
    """)

with st.sidebar.expander("Benchmark Thresholds", expanded=True):
    st.markdown("""
    **Sharpe Ratio (Is the risk worth the reward?):**
    - **Below 0.0:** Poor — earned less than a safe bank FD / bond.
    - **0.0 to 1.0:** Low — too much price swing for the profit made.
    - **1.0 to 2.0:** Good — fair reward for the risk taken.
    - **2.0 to 3.0:** Great — high returns with smooth growth.
    - **Above 3.0:** Outstanding — rare, top-performing consistency.

    ---
    **Sortino Ratio (Protection during market drops):**
    - **Below 1.0:** Weak — drops hurt your capital significantly.
    - **1.0 to 2.0:** Good — solid safety cushion during market dips.
    - **Above 2.0:** Excellent — strong gains with very little drop pain.

    ---
    **Beta (Movement vs. Nifty 50):**
    - **Below 0.8:** Defensive — falls less when the market drops.
    - **0.8 to 1.2:** Balanced — moves in step with Nifty 50.
    - **Above 1.2:** High Mover — gains faster in rallies, but drops harder in corrections.

    *Tip: If Sortino is noticeably higher than Sharpe, it means the stock's big moves were mostly upside jumps rather than downside drops.*
    """)

# ---------------------------------------------------------
# Minimal Header
# ---------------------------------------------------------
nifty_last_date_pill = ""
if not stage_toggle:
    latest_nifty_date = (
        common_dates.max()
        if not common_dates.empty
        else (data["date"].max() if not data.empty and "date" in data.columns else None)
    )
    if latest_nifty_date:
        try:
            last_date_fmt = pd.to_datetime(latest_nifty_date).strftime("%d %b %Y")
        except Exception:
            last_date_fmt = str(latest_nifty_date)
    else:
        last_date_fmt = "N/A"

    nifty_last_date_pill = f"""
        <div class="meta-item">
            <span class="meta-label">Last Fetch Date:</span>
            <span class="meta-val">{last_date_fmt}</span>
        </div>"""

st.markdown(f"""
<div class="header-container">
    <h1 class="main-title">Stock Risk-Adjusted Screener</h1>
    <div class="meta-row">
        <div class="meta-item">
            <span class="meta-label">Benchmark:</span>
            <span class="meta-val">Nifty 50</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Risk-Free Rate:</span>
            <span class="meta-val">{RISK_FREE_RATE*100:.1f}% (India 10Y G-Sec)</span>
        </div>
        <div class="meta-item">
            <span class="meta-label">Period:</span>
            <span class="meta-val">{horizon_choice}</span>
        </div>{nifty_last_date_pill}
    </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Unified Data Pipeline: Resolve Active Data
# ---------------------------------------------------------
if stage_toggle:
    if "custom_stocks" not in st.session_state:
        st.session_state.custom_stocks = []

    bench_live = load_realtime_benchmark().sort_index()
    active_bench = bench_live.tail(trading_days).sort_index()

    active_tickers = []
    custom_series = {}
    all_fetched_series = [bench_live]

    for t in st.session_state.custom_stocks:
        ok, s_5y, _ = load_realtime_stock(t)
        if ok and s_5y is not None and not s_5y.empty:
            all_fetched_series.append(s_5y)
            s_sorted = s_5y.sort_index()
            common = s_sorted.index.intersection(active_bench.index).sort_values()
            s_horizon = s_sorted.loc[common].dropna()
            if len(s_horizon) >= 30:
                custom_series[t] = s_horizon
                active_tickers.append(t)

    active_returns = pd.DataFrame(custom_series).sort_index() if custom_series else pd.DataFrame(index=active_bench.index)
    if all_fetched_series:
        min_fetch_date = min(s.index.min() for s in all_fetched_series)
        max_fetch_date = max(s.index.max() for s in all_fetched_series)
        fetch_start_fmt = pd.to_datetime(min_fetch_date).strftime("%d %b %Y")
        fetch_end_fmt = pd.to_datetime(max_fetch_date).strftime("%d %b %Y")
    else:
        fetch_start_fmt, fetch_end_fmt = "N/A", "N/A"
else:
    active_returns = pivot_returns.tail(trading_days)
    active_bench = bench_series.loc[active_returns.index]
    active_tickers = active_returns.columns.tolist()

active_scorecard = build_scorecard(active_tickers, active_returns, active_bench)

# ---------------------------------------------------------
# Custom Watchlist Input & Management (Only in Custom Mode)
# ---------------------------------------------------------
if stage_toggle:
    st.subheader("Custom Watchlist")
    st.caption(
        f"Add Indian stocks to screen and compare (e.g. `INFY`, `RELIANCE`, `TCS`, `HDFCBANK`). "
        f"Rankings and deep-dive charts will update for your selected stocks.  \n"
        f"📅 **Data Period(5 year):** from **{fetch_start_fmt}** to **{fetch_end_fmt}**"
    )

    def handle_add():
        val = st.session_state.get("ticker_input", "").strip()
        if not val:
            return

        if len(st.session_state.custom_stocks) >= 5:
            st.toast("Limit reached! You can add up to 5 stocks at a time. Delete one to add another.", icon="⚠️")
            st.session_state["ticker_input"] = ""
            return

        with st.spinner(f"Fetching 5-year market data for '{val}'..."):
            ok, s, msg = load_realtime_stock(val)

        if ok and s is not None and not s.empty:
            resolved_ticker = s.name if s.name else val.upper()
            if resolved_ticker in st.session_state.custom_stocks:
                st.toast(f"'{resolved_ticker}' is already in your stock list.", icon="⚠️")
            else:
                st.session_state.custom_stocks.append(resolved_ticker)
                st.toast(f"Added '{resolved_ticker}'! ({len(st.session_state.custom_stocks)}/5)", icon="✅")
        else:
            err_msg = msg if msg else f"Could not find '{val}'. Check the symbol."
            st.toast(err_msg, icon="❌")

        st.session_state["ticker_input"] = ""

    col_add_area, col_cards_box = st.columns([1, 1.3], gap="medium")
    is_limit_reached = len(st.session_state.custom_stocks) >= 5

    with col_add_area:
        st.markdown("**Add a Stock**")
        sub_c_in, sub_c_add = st.columns([3.2, 1.3])
        with sub_c_in:
            st.text_input(
                "Stock Symbol",
                placeholder="Enter stock symbol (e.g. TITAN, RELIANCE, INFY  ..)" if not is_limit_reached else "5-stock limit reached",
                label_visibility="collapsed",
                key="ticker_input",
                on_change=handle_add,
                disabled=is_limit_reached
            )
        with sub_c_add:
            st.button(
                "Add Stock",
                type="primary",
                width="stretch",
                on_click=handle_add,
                disabled=is_limit_reached
            )
        if is_limit_reached:
            st.caption("5-stock limit reached. Remove a stock to add another.")
        else:
            st.caption(f"Max 5 stocks • **{5 - len(st.session_state.custom_stocks)} slots left**")

    with col_cards_box:
        with st.container(border=True):
            box_h1, box_h2 = st.columns([3, 1])
            with box_h1:
                st.markdown(f"**Your Watchlist ({len(st.session_state.custom_stocks)} / 5)**")
            with box_h2:
                if st.session_state.custom_stocks:
                    if st.button("Clear All", key="btn_clear_all_custom", width="stretch"):
                        st.session_state.custom_stocks = []
                        load_realtime_stock.clear()
                        load_realtime_benchmark.clear()
                        st.rerun()

            if st.session_state.custom_stocks:
                num_stocks = len(st.session_state.custom_stocks)
                cols_count = min(num_stocks, 3)
                card_cols = st.columns(cols_count)
                for idx, t in enumerate(st.session_state.custom_stocks):
                    with card_cols[idx % cols_count]:
                        if st.button(f"✕ {t}", key=f"card_del_{t}", width="stretch", help=f"Click to remove {t}"):
                            st.session_state.custom_stocks.remove(t)
                            st.toast(f"Removed {t}")
                            st.rerun()
            else:
                st.info("No stocks added yet. Type a stock symbol on the left to add.")


# ---------------------------------------------------------
# 3 Divisions (Tabs with Default Streamlit Styling)
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "Stock Rankings",
    "Compare Stocks",
    "Stock Deep Dive"
])

# ---------------------------------------------------------
# Division 1: Stock Rankings
# ---------------------------------------------------------
with tab1:
    st.subheader("Stock Rankings")
    st.caption("Stocks ranked from highest to lowest Sharpe ratio (return per unit of risk).")
    if active_scorecard.empty:
        st.info("No stocks available to rank. Add stocks in the section above.")
    else:
        st.dataframe(
            active_scorecard.style.format({
                "CAGR": "{:.2%}", 
                "Volatility": "{:.2%}", 
                "Sharpe": "{:.2f}", 
                "Sortino": "{:.2f}", 
                "Max Drawdown": "{:.2%}", 
                "Beta": "{:.2f}", 
                "1D 95% VaR": "{:.2%}"
            }),
            width="stretch"
        )
        top_stock = active_scorecard.iloc[0]
        st.info(f"**Takeaway:** `{top_stock['Ticker']}` ranks **#1** overall with the best risk-adjusted return (Sharpe: **{top_stock['Sharpe']:.2f}**, CAGR: **{top_stock['CAGR']:.1%}**).")

# ---------------------------------------------------------
# Division 2: Head-to-Head Comparison
# ---------------------------------------------------------
with tab2:
    st.subheader("Stock Comparison")
    if len(active_tickers) < 2:
        st.info("Please have at least 2 stocks in your stock list above to compare them side-by-side.")
    else:
        if stage_toggle:
            default_selection = active_tickers[:min(2, len(active_tickers))]
        else:
            default_selection = [t for t in ["TCS.NS", "INFY.NS", "HDFCBANK.NS"] if t in active_tickers][:2]
            if len(default_selection) < 2 and len(active_tickers) >= 2:
                default_selection = active_tickers[:2]

        selected = st.multiselect(
            "Choose 2 to 4 stocks to compare", 
            active_tickers, 
            default=default_selection,
            max_selections=4
        )

        if len(selected) >= 2:
            # 1. Summary Callout
            selected_scores = active_scorecard[active_scorecard["Ticker"].isin(selected)]
            if not selected_scores.empty:
                best_sharpe = selected_scores.loc[selected_scores["Sharpe"].idxmax()]
                safest = selected_scores.loc[selected_scores["Max Drawdown"].idxmax()]
                highest_cagr = selected_scores.loc[selected_scores["CAGR"].idxmax()]

                if best_sharpe["Ticker"] == safest["Ticker"]:
                    verdict_msg = f"**Summary:** `{best_sharpe['Ticker']}` leads in both return and capital safety — delivering the highest Sharpe (**{best_sharpe['Sharpe']:.2f}**) and the smallest drop from peak (**{safest['Max Drawdown']:.1%}**)."
                else:
                    verdict_msg = f"**Summary:** `{best_sharpe['Ticker']}` offers the best return for the risk taken (Sharpe: **{best_sharpe['Sharpe']:.2f}**), while `{safest['Ticker']}` held up best during declines with a maximum drop of **{safest['Max Drawdown']:.1%}**."
                st.info(verdict_msg)

            # 2. Key Numbers Side-by-Side Table
            st.subheader("Metrics Side-by-Side")
            formatted_df = format_comparison_table(active_scorecard, selected)
            st.dataframe(formatted_df, width="stretch")

            # 3. Growth Comparison (% Total Return)
            st.subheader("Cumulative Growth")
            st.caption("How an investment in each stock grew over the selected period.")
            fig_growth = plot_cumulative_growth(selected, active_returns)
            render_chart(fig_growth)

            # Growth Takeaway
            growth_perf = {}
            for t in selected:
                if t in active_returns.columns:
                    s_ret = active_returns[t].dropna().sort_index()
                    cum_ret = ((1.0 + s_ret).cumprod() - 1.0) * 100.0
                    growth_perf[t] = cum_ret.iloc[-1] if not cum_ret.empty else 0.0
            if growth_perf:
                top_growth = max(growth_perf, key=growth_perf.get)
                bot_growth = min(growth_perf, key=growth_perf.get)
                if top_growth == bot_growth or len(growth_perf) == 1:
                    st.info(f"**Takeaway:** `{top_growth}` grew by **{growth_perf[top_growth]:+.1f}%** over this period.")
                else:
                    st.info(f"**Takeaway:** `{top_growth}` had the highest total gain (**{growth_perf[top_growth]:+.1f}%**), while `{bot_growth}` grew by **{growth_perf[bot_growth]:+.1f}%**.")

            # 4. Drawdowns from Peak
            st.subheader("Drawdowns from Peak")
            st.caption("How far each stock fell from its previous high point before recovering.")
            fig_dd = plot_drawdown_curves(selected, active_returns, selected_scores)
            render_chart(fig_dd)

            # Crash Takeaway
            if not selected_scores.empty:
                safest_dd = selected_scores.loc[selected_scores["Max Drawdown"].idxmax()]
                worst_dd = selected_scores.loc[selected_scores["Max Drawdown"].idxmin()]
                if safest_dd["Ticker"] == worst_dd["Ticker"]:
                    st.info(f"**Takeaway:** `{safest_dd['Ticker']}` had a maximum drop of **{safest_dd['Max Drawdown']:.1%}** from its peak.")
                else:
                    st.info(f"**Takeaway:** `{safest_dd['Ticker']}` had the smallest decline (**{safest_dd['Max Drawdown']:.1%}**), while `{worst_dd['Ticker']}` experienced a peak drop of **{worst_dd['Max Drawdown']:.1%}**.")

            # 5. Risk Overlap (Correlation Matrix)
            st.subheader("Stock Correlation")
            st.caption("How closely daily price movements match. Lower numbers mean better diversification.")

            corr_matrix = active_returns[selected].corr().fillna(0.0)
            fig_corr = plot_correlation_matrix(corr_matrix)
            render_chart(fig_corr)

            # Correlation takeaway
            pair_list = []
            for i in range(len(selected)):
                for j in range(i + 1, len(selected)):
                    raw_corr = corr_matrix.iloc[i, j]
                    val = 0.0 if np.isnan(raw_corr) else float(raw_corr)
                    pair_list.append((selected[i], selected[j], val))
            if len(pair_list) == 1:
                p = pair_list[0]
                desc = "low correlation, good diversification" if p[2] < 0.5 else "higher correlation, stocks tend to move together"
                st.info(f"**Takeaway:** `{p[0]}` & `{p[1]}` show a correlation of **{p[2]:.2f}** ({desc}).")
            elif len(pair_list) > 1:
                pair_list.sort(key=lambda x: x[2])
                best_p = pair_list[0]
                worst_p = pair_list[-1]
                st.info(f"**Takeaway:** `{best_p[0]}` & `{best_p[1]}` offer the best diversification (correlation: **{best_p[2]:.2f}**). `{worst_p[0]}` & `{worst_p[1]}` move together the most (**{worst_p[2]:.2f}**).")
        else:
            st.info("Please pick at least 2 stocks to compare.")

# ---------------------------------------------------------
# Division 3: Stock Deep Dive
# ---------------------------------------------------------
with tab3:
    st.subheader("Stock Deep Dive")
    if not active_tickers or active_scorecard.empty:
        st.info("No stocks available. Add stocks in the section above to inspect.")
    else:
        target_ticker = st.selectbox("Choose a Stock", active_tickers)

        matching_rows = active_scorecard[active_scorecard["Ticker"] == target_ticker]
        if matching_rows.empty:
            st.info(f"No metric data available for {target_ticker}.")
        else:
            stock_row = matching_rows.iloc[0]
            stock_ret = active_returns[target_ticker].dropna().sort_index()

            # Pre-compute growth numbers for health checks and charts
            common_idx = stock_ret.index.intersection(active_bench.index).sort_values()
            aligned_stock = stock_ret.loc[common_idx]
            aligned_bench = active_bench.loc[common_idx]

            stock_cum = ((1.0 + aligned_stock).cumprod() - 1.0) * 100.0
            bench_cum = ((1.0 + aligned_bench).cumprod() - 1.0) * 100.0

            stock_total = stock_cum.iloc[-1] if not stock_cum.empty else 0.0
            bench_total = bench_cum.iloc[-1] if not bench_cum.empty else 0.0
            diff = stock_total - bench_total

            # 1. Complete 8-Card Metric Grid (2 Rows of 4 Cards)
            r1_col1, r1_col2, r1_col3, r1_col4 = st.columns(4)
            r1_col1.metric("CAGR", f"{stock_row['CAGR']:.2%}", help="Average yearly return over the selected period.")
            r1_col2.metric("Volatility", f"{stock_row['Volatility']:.2%}", help="Annual price fluctuation. Lower is steadier.")
            r1_col3.metric("Beta", f"{stock_row['Beta']:.2f}", help="Speed vs. Nifty 50 (> 1.0 faster, < 1.0 steadier).")
            r1_col4.metric("Risk Profile", stock_row["Risk Profile"], help="Category based on returns vs. risk.")

            r2_col1, r2_col2, r2_col3, r2_col4 = st.columns(4)
            r2_col1.metric("Sharpe Ratio", f"{stock_row['Sharpe']:.2f}", help="Reward vs. risk compared to a safe bank FD (> 1.0 is great, < 0 means worse than an FD).")
            r2_col2.metric("Sortino Ratio", f"{stock_row['Sortino']:.2f}", help="Reward vs. painful drops only (ignores upside rallies).")
            r2_col3.metric("Max Drawdown", f"{stock_row['Max Drawdown']:.2%}", help="Deepest drop from peak price over the period.")
            r2_col4.metric("1D 95% VaR", f"-{abs(stock_row['1D 95% VaR']):.2%}", help="Largest likely 1-day drop on 95 out of 100 trading days.")

            # Calculate institutional metrics: Downside Capture, Upside Capture, and Underwater Time
            down_cap = compute_downside_capture(aligned_stock, aligned_bench)
            up_cap = compute_upside_capture(aligned_stock, aligned_bench)
            uw_stats = compute_underwater_stats(stock_ret)
            max_uw_days = uw_stats["max_days"]
            curr_uw_days = uw_stats["curr_days"]
            curr_dd = uw_stats["curr_dd"]
            uw_months = uw_stats["approx_months"]

            # 2. Human-Curated Verdict Rationale (Clear, Plain-English Advisory Takeaways)
            profile = str(stock_row["Risk Profile"])
            cagr_val = float(stock_row["CAGR"]) if pd.notna(stock_row["CAGR"]) else 0.0
            vol_val = float(stock_row["Volatility"]) if pd.notna(stock_row["Volatility"]) else 0.0
            sharpe_val = float(stock_row["Sharpe"]) if pd.notna(stock_row["Sharpe"]) else 0.0
            sortino_val = float(stock_row["Sortino"]) if pd.notna(stock_row["Sortino"]) else 0.0
            mdd_val = float(stock_row["Max Drawdown"]) if pd.notna(stock_row["Max Drawdown"]) else 0.0
            beta_val = float(stock_row["Beta"]) if pd.notna(stock_row["Beta"]) else 1.0

            rf_pct = f"{RISK_FREE_RATE*100:.1f}%"
            recovery_str = f"~{uw_months} months" if uw_months >= 12 else (f"~{max_uw_days} trading days" if max_uw_days > 0 else "an extended period")

            if profile == "Quality Compounder":
                rationale = (
                    f"**Verdict: Quality Compounder (Worth the Risk)** — Strong returns with very little drama. "
                    f"This stock comfortably beat a safe {rf_pct} fixed deposit (Sharpe: **{sharpe_val:.2f}**), "
                    f"and its deepest pullback was only **{mdd_val:.1%}**. "
                    f"Most price moves were steady upward gains rather than painful drops (Sortino: **{sortino_val:.2f}**). "
                    f"A top-tier pick for long-term wealth compounding."
                )
                st.success(rationale)
            elif profile == "High-Risk Trap":
                if sharpe_val < 0:
                    rationale = (
                        f"**Verdict: High-Risk Trap (Not Worth the Risk)** — High stress, poor reward. "
                        f"The stock gave lower returns than a safe {rf_pct} bank deposit (Sharpe: **{sharpe_val:.2f}**), "
                        f"meaning investors took on stock market volatility without any extra payoff. "
                        f"On top of that, it suffered a brutal **{mdd_val:.1%}** crash from its peak and took {recovery_str} "
                        f"just to break even (volatility: **{vol_val:.1%}**). Not worth the capital risk."
                    )
                elif mdd_val <= -0.38:
                    rationale = (
                        f"**Verdict: High-Risk Trap (High Pain Despite Returns)** — Don't let headline returns fool you. "
                        f"While overall gains beat a basic FD (Sharpe: **{sharpe_val:.2f}**), the stock puts your money through severe crashes. "
                        f"It plunged **{mdd_val:.1%}** from its top and experienced wild price swings (**{vol_val:.1%}** volatility), "
                        f"requiring {recovery_str} just to claw back to even. Only hold if you can stomach gut-wrenching drawdowns."
                    )
                else:
                    rationale = (
                        f"**Verdict: High-Risk Trap (Poor Risk-Reward)** — The returns don't justify the wild ride. "
                        f"A weak Sharpe ratio of **{sharpe_val:.2f}** shows that you're taking on big price swings (**{vol_val:.1%}** volatility) "
                        f"and a steep **{mdd_val:.1%}** drop from the peak, without getting enough profit over a safe {rf_pct} fixed deposit. "
                        f"Better risk-reward opportunities exist elsewhere."
                    )
                st.warning(rationale)
            elif profile == "Defensive Preserver":
                if sharpe_val < 0:
                    rationale = (
                        f"**Verdict: Defensive Preserver (Capital Shield)** — Slow and steady capital protector. "
                        f"Even though returns lagged a {rf_pct} bank deposit (Sharpe: **{sharpe_val:.2f}**), "
                        f"it did its main job: protecting your money during market turmoil. "
                        f"It moves much slower than the overall market (low Beta: **{beta_val:.2f}x**) and restricted its deepest drop to just **{mdd_val:.1%}**. "
                        f"Acts as a shock absorber during market corrections."
                    )
                else:
                    rationale = (
                        f"**Verdict: Defensive Preserver (Low-Stress Grower)** — Safe and dependable. "
                        f"It beat a safe {rf_pct} fixed deposit (Sharpe: **{sharpe_val:.2f}**) while barely flinching during market panics (low Beta: **{beta_val:.2f}x**). "
                        f"With a shallow worst drop of just **{mdd_val:.1%}**, this is a sleep-well-at-night stock that protects your capital when broader markets fall."
                    )
                st.success(rationale)
            elif profile == "High Beta Cyclical":
                if sharpe_val < 0:
                    rationale = (
                        f"**Verdict: High Beta Cyclical (Turbulent & Lagging)** — A bumpy ride that didn't pay off. "
                        f"This stock moves **{beta_val:.2f}x** faster than the Nifty, meaning it falls much harder when the market turns. "
                        f"It failed to beat a safe {rf_pct} bank deposit (Sharpe: **{sharpe_val:.2f}**) while putting investors through heavy swings "
                        f"(**{vol_val:.1%}** volatility) and a deep **{mdd_val:.1%}** drop. Demands strict risk management."
                    )
                else:
                    rationale = (
                        f"**Verdict: High Beta Cyclical (Aggressive Market Runner)** — High-energy market runner. "
                        f"The stock delivered solid gains above a safe {rf_pct} deposit (Sharpe: **{sharpe_val:.2f}**), "
                        f"but it swings aggressively (**{beta_val:.2f}x** market speed, **{vol_val:.1%}** volatility). "
                        f"It surges during market rallies, but also took a sharp **{mdd_val:.1%}** hit during market pullbacks. "
                        f"Best suited for active investors who can ride out steep corrections."
                    )
                st.info(rationale)
            else:
                if sharpe_val < 0:
                    rationale = (
                        f"**Verdict: Moderate Compounder (Lacking Momentum)** — Disciplined behavior, but lagged safe returns. "
                        f"Over this period, returns fell behind a {rf_pct} bank deposit (Sharpe: **{sharpe_val:.2f}**). "
                        f"On the bright side, it didn't suffer disastrous crashes—holding volatility to **{vol_val:.1%}** "
                        f"and limiting its worst drop to **{mdd_val:.1%}**. A steady stock waiting for better earnings momentum."
                    )
                else:
                    rationale = (
                        f"**Verdict: Moderate Compounder (Solid Core Holding)** — Dependable, balanced performer. "
                        f"The stock earned a healthy return above a safe {rf_pct} fixed deposit (Sharpe: **{sharpe_val:.2f}**) "
                        f"without subjecting investors to wild swings. With normal volatility (**{vol_val:.1%}**) "
                        f"and a manageable worst drop of **{mdd_val:.1%}**, it serves as a steady, low-drama core portfolio holding."
                    )
                st.info(rationale)

            # 3. Key Health Checks (Simple Practical Checks)
            st.subheader("Key Health Checks")

            chk_col1, chk_col2, chk_col3 = st.columns(3)

            # Card 1: Market Crash Cushion (Downside Capture vs. Nifty Red Days)
            with chk_col1:
                if down_cap <= 0.80:
                    if down_cap < 0:
                        st.success(
                            f"**Market Crash Cushion:** Exceptional (**{down_cap:.0%}** capture)  \n"
                            f"Stayed green or held flat even when the market tumbled. Excellent protection."
                        )
                    else:
                        pct_less = (1.0 - down_cap) * 100.0
                        st.success(
                            f"**Market Crash Cushion:** Strong (**{down_cap:.0%}** capture)  \n"
                            f"Falls **{pct_less:.0f}% less** than Nifty on bad days. Great cushion during market pullbacks."
                        )
                elif down_cap <= 1.15:
                    st.info(
                        f"**Market Crash Cushion:** Balanced (**{down_cap:.0%}** capture)  \n"
                        f"Moves roughly in step with Nifty on bad days. Typical market risk."
                    )
                else:
                    mult = down_cap
                    st.warning(
                        f"**Market Crash Cushion:** Sensitive (**{down_cap:.0%}** capture)  \n"
                        f"Falls **{mult:.1f}x harder** than Nifty on bad days. Deepens losses during market sell-offs."
                    )

            # Card 2: Gain vs. Pain Quality (Upside / Downside Capture Ratio & Asymmetry)
            with chk_col2:
                if up_cap >= 1.12 * down_cap and sortino_val >= 0.5:
                    st.success(
                        f"**Gain vs. Pain:** Favorable (**{up_cap:.0%}** Up / **{down_cap:.0%}** Down)  \n"
                        f"Captures **{up_cap:.0%}** of market rallies but only **{down_cap:.0%}** of drops. Rises much faster than it falls."
                    )
                elif up_cap >= 0.88 * down_cap:
                    st.info(
                        f"**Gain vs. Pain:** Balanced (**{up_cap:.0%}** Up / **{down_cap:.0%}** Down)  \n"
                        f"Captures **{up_cap:.0%}** of rallies and **{down_cap:.0%}** of drops. Moves fairly evenly with the market up and down."
                    )
                else:
                    st.warning(
                        f"**Gain vs. Pain:** Unfavorable (**{up_cap:.0%}** Up / **{down_cap:.0%}** Down)  \n"
                        f"Misses out on rallies (**{up_cap:.0%}**) but takes heavier hits on drops (**{down_cap:.0%}**). Poor reward for the risk taken."
                    )

            # Card 3: Rebound Patience (Time Underwater / Slump Duration)
            with chk_col3:
                if curr_uw_days == 0:
                    live_note = "Currently trading near its peak."
                else:
                    live_note = f"Currently {curr_uw_days} days into a dip ({curr_dd:.1%} below peak)."

                if max_uw_days <= 65:
                    mos_str = f"~{max(1, uw_months)} mos" if max_uw_days >= 15 else "<1 mo"
                    st.success(
                        f"**Rebound Patience:** Fast (**{max_uw_days}d** / {mos_str})  \n"
                        f"Bounced back quickly after pullbacks. Rarely stays down for long.  \n"
                        f"*{live_note}*"
                    )
                elif max_uw_days <= 180:
                    st.info(
                        f"**Rebound Patience:** Normal (**{max_uw_days}d** / ~{uw_months} mos)  \n"
                        f"Took about ~{uw_months} months to recover from its worst slump. Typical recovery pace.  \n"
                        f"*{live_note}*"
                    )
                else:
                    st.warning(
                        f"**Rebound Patience:** Demanding (**{max_uw_days}d** / ~{uw_months} mos)  \n"
                        f"Took ~{uw_months} months to claw back from its biggest drop. Requires high patience during downturns.  \n"
                        f"*{live_note}*"
                    )

            # 4. Performance Comparison vs. Benchmark
            st.subheader("Return vs. Nifty 50")
            st.caption("How this stock grew compared to the Nifty 50 index over time.")
            fig_bench = plot_benchmark_comparison(target_ticker, stock_cum, bench_cum, stock_total, bench_total)
            render_chart(fig_bench)

            # Benchmark Takeaway
            if diff >= 0:
                st.info(f"**Takeaway:** `{target_ticker}` beat Nifty 50 by **+{diff:.1f}%** over this period (**{stock_total:+.1f}%** vs. **{bench_total:+.1f}%**).")
            else:
                st.info(f"**Takeaway:** `{target_ticker}` trailed Nifty 50 by **-{abs(diff):.1f}%** over this period (**{stock_total:+.1f}%** vs. **{bench_total:+.1f}%**).")

            # 5. Daily Price Swings & Worst 1-Day Drop Limit
            st.subheader("Daily Swings & 1-Day Loss Limit (VaR)")
            st.caption("Daily price swings. The red line marks the 95% worst-day loss limit.")
            var_cutoff = -abs(stock_row["1D 95% VaR"]) * 100
            fig_hist = plot_var_histogram(stock_ret, var_cutoff)
            render_chart(fig_hist)

            st.info(f"**Takeaway:** On 95 out of 100 days, daily losses stayed within **{abs(stock_row['1D 95% VaR']):.2%}**. The single worst 1-day drop was **{stock_ret.min():.2%}**.")
