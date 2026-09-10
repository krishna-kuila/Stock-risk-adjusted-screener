import unittest
import numpy as np
import pandas as pd
from src.metrics import (
    compute_cagr, compute_volatility, compute_drawdown_series,
    compute_beta, compute_var_historical
)
from src.scoring import build_scorecard
from src.fetcher import fetch_stock_returns


class TestQuantMetricsPrecision(unittest.TestCase):

    def setUp(self):
        np.random.seed(42)
        dates = pd.date_range("2024-01-01", periods=252, freq="B").strftime("%Y-%m-%d")
        daily_ret = np.random.normal(0.0008, 0.015, size=252)
        self.stock_returns = pd.Series(daily_ret, index=dates, name="TEST_STOCK")
        
        bench_ret = np.random.normal(0.0005, 0.012, size=252)
        self.bench_returns = pd.Series(bench_ret, index=dates, name="^NSEI")

    def test_cagr_calculation(self):
        cagr = compute_cagr(self.stock_returns)
        self.assertTrue(np.isfinite(cagr))
        # Total compounded return
        compounded = (1.0 + self.stock_returns).prod()
        expected = compounded ** (1.0 / 1.0) - 1.0
        self.assertAlmostEqual(cagr, expected, places=5)

    def test_volatility_annualized(self):
        vol = compute_volatility(self.stock_returns)
        expected = self.stock_returns.std(ddof=1) * np.sqrt(252)
        self.assertAlmostEqual(vol, expected, places=5)

    def test_drawdown_monotonic_sorting(self):
        # Even if index is shuffled, compute_drawdown_series sorts chronologically
        shuffled = self.stock_returns.sample(frac=1.0, random_state=123)
        dd_shuffled = compute_drawdown_series(shuffled)
        dd_ordered = compute_drawdown_series(self.stock_returns)
        pd.testing.assert_series_equal(dd_shuffled, dd_ordered)

    def test_beta_calculation(self):
        beta = compute_beta(self.stock_returns, self.bench_returns)
        cov = np.cov(self.stock_returns, self.bench_returns)[0, 1]
        mkt_var = np.var(self.bench_returns, ddof=1)
        self.assertAlmostEqual(beta, cov / mkt_var, places=5)

    def test_var95_calculation(self):
        var95 = compute_var_historical(self.stock_returns)
        expected = -np.percentile(self.stock_returns, 5.0)
        self.assertAlmostEqual(var95, expected, places=5)

    def test_scorecard_generation(self):
        df = pd.DataFrame({"TEST_STOCK": self.stock_returns})
        sc = build_scorecard(["TEST_STOCK"], df, self.bench_returns)
        self.assertEqual(len(sc), 1)
        row = sc.iloc[0]
        self.assertEqual(row["Ticker"], "TEST_STOCK")
        self.assertTrue(row["1D 95% VaR"] <= 0)  # Should be stored as negative

    def test_downside_and_upside_capture(self):
        from src.metrics import compute_downside_capture, compute_upside_capture
        down_cap = compute_downside_capture(self.stock_returns, self.bench_returns)
        up_cap = compute_upside_capture(self.stock_returns, self.bench_returns)
        self.assertTrue(np.isfinite(down_cap))
        self.assertTrue(np.isfinite(up_cap))
        self.assertTrue(down_cap > 0)
        self.assertTrue(up_cap > 0)

    def test_underwater_stats(self):
        from src.metrics import compute_underwater_stats
        # Synthetic known sequence: Peak on day 0, down for 3 days, new peak on day 4
        seq = pd.Series([0.10, -0.05, -0.02, -0.01, 0.15])
        stats = compute_underwater_stats(seq)
        self.assertEqual(stats["max_days"], 3)
        self.assertEqual(stats["curr_days"], 0)  # At peak on last day
        self.assertAlmostEqual(stats["curr_dd"], 0.0)

        # Sequence ending in a drawdown
        seq2 = pd.Series([0.10, 0.05, -0.04, -0.02])
        stats2 = compute_underwater_stats(seq2)
        self.assertEqual(stats2["curr_days"], 2)
        self.assertTrue(stats2["curr_dd"] < 0)


class TestLivePeriodSwitching(unittest.TestCase):

    def test_live_data_periods(self):
        ok, bench_5y, msg = fetch_stock_returns("^NSEI", period="5y")
        self.assertTrue(ok, f"Benchmark fetch failed: {msg}")
        self.assertIsNotNone(bench_5y)
        self.assertTrue(len(bench_5y) >= 1000)

        ok_s, stock_5y, msg_s = fetch_stock_returns("INFY.NS", period="5y")
        self.assertTrue(ok_s, f"Stock fetch failed: {msg_s}")
        self.assertIsNotNone(stock_5y)

        # Test each period: 1Y, 3Y, 5Y
        periods = [
            ("1 Year", 252),
            ("3 Years", 252 * 3),
            ("5 Years", 252 * 5)
        ]

        for name, td in periods:
            active_bench = bench_5y.tail(td).sort_index()
            common = stock_5y.sort_index().index.intersection(active_bench.index).sort_values()
            s_horizon = stock_5y.loc[common].dropna()
            
            returns_df = pd.DataFrame({"INFY.NS": s_horizon}).sort_index()
            sc = build_scorecard(["INFY.NS"], returns_df, active_bench)
            
            self.assertEqual(len(sc), 1)
            row = sc.iloc[0]
            
            # Verify all metrics are valid finite numbers
            for col in ["CAGR", "Volatility", "Sharpe", "Sortino", "Max Drawdown", "Beta", "1D 95% VaR"]:
                self.assertTrue(np.isfinite(row[col]), f"{col} is not finite in period {name}")

            # Verify that length reflects the period
            self.assertTrue(len(s_horizon) <= td)
            if name == "1 Year":
                self.assertTrue(len(s_horizon) >= 240)
            elif name == "3 Years":
                self.assertTrue(len(s_horizon) >= 700)

            print(f"Verified {name}: {len(s_horizon)} days, CAGR={row['CAGR']:.2%}, Sharpe={row['Sharpe']:.2f}")


if __name__ == "__main__":
    unittest.main()
