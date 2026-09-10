import pandas as pd
from config import RISK_FREE_RATE
from src.metrics import (
    compute_cagr, compute_volatility, compute_sharpe,
    compute_sortino, compute_max_drawdown, compute_beta,
    compute_var_historical
)


def categorize_stock(cagr: float, vol: float, sharpe: float, sortino: float, mdd: float, beta: float) -> str:
    """Categorizes a stock into an intuitive risk profile based on quant metrics."""
    if sharpe >= 1.0 and mdd >= -0.28:
        return "Quality Compounder"
    elif mdd <= -0.38 or vol >= 0.35:
        return "High-Risk Trap"
    elif beta < 0.85 and mdd >= -0.22:
        return "Defensive Preserver"
    elif beta >= 1.25:
        return "High Beta Cyclical"
    else:
        return "Moderate Compounder"


def build_scorecard(tickers: list[str], returns_df: pd.DataFrame, bench_s: pd.Series) -> pd.DataFrame:
    """Builds a complete risk-adjusted scorecard for a list of tickers."""
    summary = []
    for ticker in tickers:
        if ticker not in returns_df.columns:
            continue
        r = returns_df[ticker].dropna()
        if len(r) < 30:
            continue
        cagr = compute_cagr(r)
        vol = compute_volatility(r)
        sharpe = compute_sharpe(r, RISK_FREE_RATE)
        sortino = compute_sortino(r, RISK_FREE_RATE)
        mdd = compute_max_drawdown(r)
        beta = compute_beta(r, bench_s)
        var95 = compute_var_historical(r)
        verdict = categorize_stock(cagr, vol, sharpe, sortino, mdd, beta)

        summary.append({
            "Ticker": ticker,
            "Risk Profile": verdict,
            "CAGR": cagr,
            "Volatility": vol,
            "Sharpe": sharpe,
            "Sortino": sortino,
            "Max Drawdown": mdd,
            "Beta": beta,
            "1D 95% VaR": -abs(var95)
        })

    df_score = pd.DataFrame(summary)
    if not df_score.empty:
        df_score = df_score.sort_values("Sharpe", ascending=False).reset_index(drop=True)
        df_score.index += 1
    return df_score


def format_comparison_table(scorecard_df: pd.DataFrame, selected_tickers: list[str]) -> pd.DataFrame:
    """Formats a side-by-side transposed metric comparison table for selected tickers."""
    if scorecard_df.empty or not selected_tickers:
        return pd.DataFrame()
    comp_metrics = scorecard_df[scorecard_df["Ticker"].isin(selected_tickers)].set_index("Ticker")
    ordered = [t for t in selected_tickers if t in comp_metrics.index]
    comp_metrics = comp_metrics.reindex(ordered)
    cols = ["Risk Profile", "CAGR", "Volatility", "Sharpe", "Sortino", "Max Drawdown", "Beta", "1D 95% VaR"]
    display_metrics = comp_metrics[[c for c in cols if c in comp_metrics.columns]].T

    formatted_dict = {}
    for col in display_metrics.columns:
        formatted_dict[col] = [
            f"{val:.2%}" if metric in ["CAGR", "Volatility", "Max Drawdown", "1D 95% VaR"]
            else (f"{val:.2f}" if isinstance(val, (int, float)) and not pd.isna(val) else str(val if not pd.isna(val) else "N/A"))
            for metric, val in display_metrics[col].items()
        ]
    return pd.DataFrame(formatted_dict, index=display_metrics.index)
