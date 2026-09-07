import numpy as np
import pandas as pd
from scipy.stats import norm
from config import TRADING_DAYS_PER_YEAR, RISK_FREE_RATE


def calculate_daily_rf(annual_rf: float = RISK_FREE_RATE) -> float:
    return (1.0 + annual_rf) ** (1.0 / TRADING_DAYS_PER_YEAR) - 1.0


def compute_cagr(returns: pd.Series) -> float:
    clean_returns = returns.dropna()
    n_days = len(clean_returns)
    if n_days == 0:
        return 0.0
    num_years = n_days / TRADING_DAYS_PER_YEAR
    compounded = np.exp(np.log1p(clean_returns).sum())
    return float((compounded ** (1.0 / num_years)) - 1.0) if num_years > 0 else 0.0


def compute_volatility(returns: pd.Series) -> float:
    clean_returns = returns.dropna()
    return float(clean_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)) if len(clean_returns) > 1 else 0.0


def compute_sharpe(returns: pd.Series, annual_rf: float = RISK_FREE_RATE) -> float:
    clean_returns = returns.dropna()
    if len(clean_returns) < 2:
        return 0.0
    daily_rf = calculate_daily_rf(annual_rf)
    excess_returns = clean_returns - daily_rf
    std = clean_returns.std(ddof=1)
    return float(np.sqrt(TRADING_DAYS_PER_YEAR) * (excess_returns.mean() / std)) if std > 0 else 0.0


def compute_sortino(returns: pd.Series, annual_rf: float = RISK_FREE_RATE) -> float:
    clean_returns = returns.dropna()
    if len(clean_returns) < 2:
        return 0.0
    daily_rf = calculate_daily_rf(annual_rf)
    excess_returns = clean_returns - daily_rf
    downside_deviations = np.minimum(0.0, excess_returns)# Clip upside to 0, keeping all N observations in the denominator
    downside_variance = np.mean(downside_deviations ** 2)
    downside_std = np.sqrt(downside_variance)
    return float(np.sqrt(TRADING_DAYS_PER_YEAR) * (excess_returns.mean() / downside_std)) if downside_std > 0 else 0.0


def compute_drawdown_series(returns: pd.Series) -> pd.Series:
    wealth = (1.0 + returns.fillna(0.0)).cumprod()
    peaks = wealth.cummax()
    return (wealth - peaks) / peaks


def compute_max_drawdown(returns: pd.Series) -> float:
    dd = compute_drawdown_series(returns)
    return float(dd.min()) if not dd.empty else 0.0


def compute_beta(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    aligned = pd.concat([stock_returns, market_returns], axis=1, join="inner").dropna()
    if len(aligned) < 30:
        return 1.0
    cov_matrix = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])
    cov = cov_matrix[0, 1]
    mkt_var = cov_matrix[1, 1]
    return float(cov / mkt_var) if mkt_var > 0 else 1.0


def compute_var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    clean_returns = returns.dropna()
    if clean_returns.empty:
        return 0.0
    return float(-np.percentile(clean_returns, (1.0 - confidence) * 100))