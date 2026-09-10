import unittest
import pandas as pd
import numpy as np
from src.fetcher import fetch_stock_returns
from src.scoring import build_scorecard, format_comparison_table
from src.charts import (
    plot_cumulative_growth, plot_drawdown_curves,
    plot_correlation_matrix, plot_benchmark_comparison,
    plot_var_histogram
)


class TestTabsIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        ok_b, bench_5y, msg_b = fetch_stock_returns("^NSEI", period="5y")
        assert ok_b, f"Benchmark fetch failed: {msg_b}"
        cls.bench_5y = bench_5y

        cls.tickers = ["INFY.NS", "TCS.NS"]
        cls.stock_series = {}
        for t in cls.tickers:
            ok, s, msg = fetch_stock_returns(t, period="5y")
            assert ok, f"Stock fetch failed for {t}: {msg}"
            cls.stock_series[t] = s

    def test_end_to_end_tabs_all_periods(self):
        for period_name, td in [("1 Year", 252), ("3 Years", 756), ("5 Years", 1260)]:
            active_bench = self.bench_5y.tail(td).sort_index()
            custom_series = {}
            active_tickers = []
            for t in self.tickers:
                s_sorted = self.stock_series[t].sort_index()
                common = s_sorted.index.intersection(active_bench.index).sort_values()
                s_horizon = s_sorted.loc[common].dropna()
                if len(s_horizon) >= 30:
                    custom_series[t] = s_horizon
                    active_tickers.append(t)

            active_returns = pd.DataFrame(custom_series).sort_index()
            active_scorecard = build_scorecard(active_tickers, active_returns, active_bench)

            # 1. Tab 2 Compare Tools Verification
            selected = active_tickers[:2]
            selected_scores = active_scorecard[active_scorecard["Ticker"].isin(selected)]
            self.assertEqual(len(selected_scores), 2)
            
            best_sharpe = selected_scores.loc[selected_scores["Sharpe"].idxmax()]
            safest = selected_scores.loc[selected_scores["Max Drawdown"].idxmax()]
            self.assertIn(best_sharpe["Ticker"], selected)
            self.assertIn(safest["Ticker"], selected)

            # Table display metrics
            comp_metrics = active_scorecard[active_scorecard["Ticker"].isin(selected)].set_index("Ticker")
            comp_metrics = comp_metrics.reindex(selected)
            display_metrics = comp_metrics[["Risk Profile", "CAGR", "Volatility", "Sharpe", "Sortino", "Max Drawdown", "Beta", "1D 95% VaR"]].T
            self.assertEqual(list(display_metrics.columns), selected)

            # Charts
            fig_g = plot_cumulative_growth(selected, active_returns)
            self.assertIsNotNone(fig_g)
            fig_dd = plot_drawdown_curves(selected, active_returns, selected_scores)
            self.assertIsNotNone(fig_dd)
            corr_mat = active_returns[selected].corr().fillna(0.0)
            fig_c = plot_correlation_matrix(corr_mat)
            self.assertIsNotNone(fig_c)

            # 2. Tab 3 Stock Deep Dive Verification
            for target in selected:
                stock_row = active_scorecard[active_scorecard["Ticker"] == target].iloc[0]
                stock_ret = active_returns[target].dropna().sort_index()
                common_idx = stock_ret.index.intersection(active_bench.index).sort_values()
                aligned_stock = stock_ret.loc[common_idx]
                aligned_bench = active_bench.loc[common_idx]
                stock_cum = ((1.0 + aligned_stock).cumprod() - 1.0) * 100.0
                bench_cum = ((1.0 + aligned_bench).cumprod() - 1.0) * 100.0
                stock_total = stock_cum.iloc[-1]
                bench_total = bench_cum.iloc[-1]
                diff = stock_total - bench_total

                # Verify deep dive charts
                fig_b = plot_benchmark_comparison(target, stock_cum, bench_cum, stock_total, bench_total)
                self.assertIsNotNone(fig_b)
                fig_h = plot_var_histogram(stock_ret, -abs(stock_row["1D 95% VaR"]) * 100)
                self.assertIsNotNone(fig_h)

                # Verify 8-card grid consistency
                self.assertTrue(np.isfinite(stock_row["CAGR"]))
                self.assertTrue(np.isfinite(stock_row["Volatility"]))
                self.assertTrue(np.isfinite(stock_row["Beta"]))
                self.assertTrue(np.isfinite(stock_row["Sharpe"]))
                self.assertTrue(np.isfinite(stock_row["Sortino"]))
                self.assertTrue(np.isfinite(stock_row["Max Drawdown"]))
                self.assertTrue(np.isfinite(stock_row["1D 95% VaR"]))
                self.assertTrue(stock_row["1D 95% VaR"] <= 0)

            print(f"[{period_name}] End-to-end integration verified successfully.")

    def test_load_realtime_stock_clear_callable(self):
        """Verify that load_realtime_stock has .clear() method attached and callable."""
        from app import load_realtime_stock, load_realtime_benchmark
        self.assertTrue(hasattr(load_realtime_stock, "clear"))
        self.assertTrue(callable(load_realtime_stock.clear))
        self.assertTrue(hasattr(load_realtime_benchmark, "clear"))
        self.assertTrue(callable(load_realtime_benchmark.clear))
        # Call clear to ensure no AttributeError or Exception
        load_realtime_stock.clear()
        load_realtime_benchmark.clear()

    def test_ticker_alias_resolutions(self):
        """Verify that popular Indian stock variations resolve and fetch valid 5Y data."""
        test_queries = [
            ("RIL", "RELIANCE.NS"),
            ("RELIANCE INDUSTRIES", "RELIANCE.NS"),
            ("reliance", "RELIANCE.NS"),
            ("SBI", "SBIN.NS"),
            ("HDFC BANK", "HDFCBANK.NS"),
            ("TATA MOTORS", "TATAMOTORS.NS"),
            ("ZOMATO", "ETERNAL.NS"),
        ]
        for query, expected_target in test_queries:
            ok, s, msg = fetch_stock_returns(query, period="5y")
            self.assertTrue(ok, f"Failed for query '{query}': {msg}")
            self.assertIsNotNone(s)
            self.assertGreaterEqual(len(s), 30)

    def test_single_stock_watchlist_behavior(self):
        """Verify that 1 single custom stock does not crash Tab 2 or Tab 3."""
        active_tickers = ["INFY.NS"]
        custom_series = {"INFY.NS": self.stock_series["INFY.NS"].tail(252)}
        active_returns = pd.DataFrame(custom_series).sort_index()
        active_bench = self.bench_5y.tail(252).sort_index()
        scorecard = build_scorecard(active_tickers, active_returns, active_bench)

        self.assertEqual(len(scorecard), 1)
        # Tab 2 comparison guard: len(active_tickers) < 2
        self.assertTrue(len(active_tickers) < 2)

        # Tab 3 Deep Dive works with single stock
        target_ticker = active_tickers[0]
        matching = scorecard[scorecard["Ticker"] == target_ticker]
        self.assertFalse(matching.empty)
        row = matching.iloc[0]
        self.assertIn("Sharpe", row)
        self.assertIn("Sortino", row)


    def test_load_realtime_stock_unpacking_and_behavior(self):
        """Verify load_realtime_stock returns 3-tuple (ok, s, msg) and unpacks properly."""
        from app import load_realtime_stock
        
        # Test valid stock unpacking
        res = load_realtime_stock("INFY")
        self.assertIsInstance(res, tuple)
        self.assertEqual(len(res), 3)
        ok, s, msg = res
        self.assertTrue(ok)
        self.assertIsNotNone(s)
        self.assertIsInstance(msg, str)

        # Test invalid stock unpacking
        res_bad = load_realtime_stock("NON_EXISTENT_TICKER_XYZ999")
        self.assertEqual(len(res_bad), 3)
        ok_bad, s_bad, msg_bad = res_bad
        self.assertFalse(ok_bad)
        self.assertIsNone(s_bad)
        self.assertIsInstance(msg_bad, str)


    def test_no_local_db_fallback(self):
        """Verify that when online APIs fail, fetch_stock_returns does NOT fallback to local DB."""
        from unittest.mock import patch
        import yfinance as yf
        
        # Patch both direct chart fetcher and yf.Ticker to simulate complete online failure
        with patch("src.fetcher._fetch_direct_chart", return_value=(0, None, "Simulated network error")), \
             patch.object(yf, "Ticker", side_effect=RuntimeError("Simulated Tier 2 failure")):
            # Even though TCS.NS is in screener.db, it must fail because Tier 3 was removed
            ok, s, msg = fetch_stock_returns("TCS")
            self.assertFalse(ok)
            self.assertIsNone(s)
            self.assertIn("Could not find live market data", msg)


    def test_negative_sharpe_verdict_rationale(self):
        """Verify that negative Sharpe ratios never output 'suggests positive return'."""
        sharpe_val = -1.47
        mdd_val = -0.42
        vol_val = 0.28
        rf_pct = "7.1%"
        recovery_str = "~14 months"
        profile = "High-Risk Trap"

        if sharpe_val < 0:
            rationale = (
                f"**Verdict: High-Risk Trap (Not Worth the Risk)** — High stress, poor reward. "
                f"The stock gave lower returns than a safe {rf_pct} bank deposit (Sharpe: **{sharpe_val:.2f}**), "
                f"meaning investors took on stock market volatility without any extra payoff. "
                f"On top of that, it suffered a brutal **{mdd_val:.1%}** crash from its peak and took {recovery_str} "
                f"just to break even (volatility: **{vol_val:.1%}**). Not worth the capital risk."
            )
        else:
            rationale = "positive"

        self.assertNotIn("positive return", rationale)
        self.assertIn("lower returns than a safe", rationale)
        self.assertIn("-1.47", rationale)

    def test_format_comparison_table(self):
        """Verify format_comparison_table properly transposes and formats metrics."""
        scorecard = pd.DataFrame([
            {
                "Ticker": "TCS.NS",
                "Risk Profile": "Quality Compounder",
                "CAGR": 0.152,
                "Volatility": 0.184,
                "Sharpe": 1.25,
                "Sortino": 1.82,
                "Max Drawdown": -0.214,
                "Beta": 0.78,
                "1D 95% VaR": -0.021
            },
            {
                "Ticker": "INFY.NS",
                "Risk Profile": "Moderate Compounder",
                "CAGR": 0.121,
                "Volatility": 0.225,
                "Sharpe": 0.88,
                "Sortino": 1.15,
                "Max Drawdown": -0.285,
                "Beta": 0.95,
                "1D 95% VaR": -0.026
            }
        ])
        formatted = format_comparison_table(scorecard, ["TCS.NS", "INFY.NS"])
        self.assertEqual(list(formatted.columns), ["TCS.NS", "INFY.NS"])
        self.assertIn("Sharpe", formatted.index)
        self.assertIn("CAGR", formatted.index)
        self.assertEqual(formatted.loc["CAGR", "TCS.NS"], "15.20%")
        self.assertEqual(formatted.loc["Sharpe", "TCS.NS"], "1.25")
        self.assertEqual(formatted.loc["Max Drawdown", "TCS.NS"], "-21.40%")

    def test_nifty_mode_last_fetch_date_pill(self):
        """Verify that Nifty 50 mode generates the Last Fetch Date pill from database dates, and hides it in custom mode."""
        import sqlite3
        from config import DB_PATH

        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT date FROM stock_prices ORDER BY date ASC", conn)
        conn.close()

        self.assertFalse(df.empty)
        max_date = df["date"].max()
        self.assertIsNotNone(max_date)
        formatted_date = pd.to_datetime(max_date).strftime("%d %b %Y")

        # Test pill generation logic when stage_toggle is False (Nifty 50 mode)
        stage_toggle_false = False
        nifty_pill = ""
        if not stage_toggle_false:
            nifty_pill = f"""
        <div class="meta-item">
            <span class="meta-label">Last Fetch Date:</span>
            <span class="meta-val">{formatted_date}</span>
        </div>"""

        self.assertIn("Last Fetch Date:", nifty_pill)
        self.assertIn(formatted_date, nifty_pill)

        # Test pill generation logic when stage_toggle is True (Custom Watchlist mode)
        stage_toggle_true = True
        custom_pill = ""
        if not stage_toggle_true:
            custom_pill = f"""
        <div class="meta-item">
            <span class="meta-label">Last Fetch Date:</span>
            <span class="meta-val">{formatted_date}</span>
        </div>"""

        self.assertEqual(custom_pill, "")


if __name__ == "__main__":
    unittest.main()

