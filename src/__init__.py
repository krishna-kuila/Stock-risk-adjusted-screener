from src.metrics import (
    compute_cagr, compute_volatility, compute_sharpe, 
    compute_sortino, compute_max_drawdown, compute_beta, 
    compute_var_historical, compute_drawdown_series,
    compute_downside_capture, compute_upside_capture,
    compute_underwater_stats
)
from src.fetcher import fetch_stock_returns
from src.scoring import categorize_stock, build_scorecard, format_comparison_table
from src.charts import (
    plot_cumulative_growth,
    plot_drawdown_curves,
    plot_correlation_matrix,
    plot_benchmark_comparison,
    plot_var_histogram
)

__all__ = [
    'compute_cagr', 'compute_volatility', 'compute_sharpe', 
    'compute_sortino', 'compute_max_drawdown', 'compute_beta', 
    'compute_var_historical', 'compute_drawdown_series',
    'compute_downside_capture', 'compute_upside_capture',
    'compute_underwater_stats',
    'fetch_stock_returns',
    'categorize_stock', 'build_scorecard', 'format_comparison_table',
    'plot_cumulative_growth',
    'plot_drawdown_curves',
    'plot_correlation_matrix',
    'plot_benchmark_comparison',
    'plot_var_histogram'
]