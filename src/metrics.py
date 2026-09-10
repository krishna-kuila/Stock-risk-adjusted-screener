import numpy as np
import pandas as pd
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
    if not np.isfinite(compounded) or compounded <= 0:
        return -1.0
    val = (compounded ** (1.0 / num_years)) - 1.0 if num_years > 0 else 0.0
    return float(val) if np.isfinite(val) else -1.0


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
    if std <= 0 or not np.isfinite(std):
        return 0.0
    val = np.sqrt(TRADING_DAYS_PER_YEAR) * (excess_returns.mean() / std)
    return float(val) if np.isfinite(val) else 0.0


def compute_sortino(returns: pd.Series, annual_rf: float = RISK_FREE_RATE) -> float:
    clean_returns = returns.dropna()
    if len(clean_returns) < 2:
        return 0.0
    daily_rf = calculate_daily_rf(annual_rf)
    excess_returns = clean_returns - daily_rf
    downside_deviations = np.minimum(0.0, excess_returns)  # Clip upside to 0, keeping all N observations in the denominator
    downside_variance = np.mean(downside_deviations ** 2)
    downside_std = np.sqrt(downside_variance)
    if downside_std <= 0 or not np.isfinite(downside_std):
        return 0.0
    val = np.sqrt(TRADING_DAYS_PER_YEAR) * (excess_returns.mean() / downside_std)
    return float(val) if np.isfinite(val) else 0.0


def compute_drawdown_series(returns: pd.Series) -> pd.Series:
    clean_returns = returns.dropna().sort_index()
    if clean_returns.empty:
        return pd.Series(dtype=float)
    wealth = (1.0 + clean_returns).cumprod()
    peaks = wealth.cummax().clip(lower=1.0)
    safe_peaks = peaks.replace(0, np.nan)
    dd = (wealth - safe_peaks) / safe_peaks
    return dd.fillna(-1.0)


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
    if not np.isfinite(cov) or not np.isfinite(mkt_var) or mkt_var <= 0:
        return 1.0
    val = cov / mkt_var
    return float(val) if np.isfinite(val) else 1.0


def compute_var_historical(returns: pd.Series, confidence: float = 0.95) -> float:
    clean_returns = returns.dropna()
    if clean_returns.empty:
        return 0.0
    val = -np.percentile(clean_returns, (1.0 - confidence) * 100)
    return float(val) if np.isfinite(val) else 0.0


def compute_downside_capture(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    """Measures how much of the market's decline the stock absorbs on market down days.
    
    Values < 1.0 (100%) mean the stock falls less than the market (shields capital).
    Values > 1.0 (100%) mean the stock falls harder than the market on red days.
    """
    aligned = pd.concat([stock_returns, market_returns], axis=1, join="inner").dropna()
    if len(aligned) < 5:
        return 1.0
    s_ret = aligned.iloc[:, 0]
    m_ret = aligned.iloc[:, 1]
    down_days = m_ret < 0
    if down_days.sum() < 2 or abs(m_ret[down_days].mean()) < 1e-8:
        return 1.0
    val = s_ret[down_days].mean() / m_ret[down_days].mean()
    return float(val) if np.isfinite(val) else 1.0


def compute_upside_capture(stock_returns: pd.Series, market_returns: pd.Series) -> float:
    """Measures how much of the market's rally the stock captures on market up days.
    
    Values > 1.0 (100%) mean the stock outperforms the market during rallies.
    """
    aligned = pd.concat([stock_returns, market_returns], axis=1, join="inner").dropna()
    if len(aligned) < 5:
        return 1.0
    s_ret = aligned.iloc[:, 0]
    m_ret = aligned.iloc[:, 1]
    up_days = m_ret > 0
    if up_days.sum() < 2 or abs(m_ret[up_days].mean()) < 1e-8:
        return 1.0
    val = s_ret[up_days].mean() / m_ret[up_days].mean()
    return float(val) if np.isfinite(val) else 1.0


def compute_underwater_stats(returns: pd.Series) -> dict:
    """Computes time spent underwater (drawdown recovery duration) in trading days.
    
    Returns maximum consecutive trading days below previous peak, current days in drawdown,
    and current drawdown percentage.
    """
    clean_returns = returns.dropna().sort_index()
    if clean_returns.empty:
        return {"max_days": 0, "curr_days": 0, "curr_dd": 0.0, "approx_months": 0}
    wealth = (1.0 + clean_returns).cumprod()
    peaks = wealth.cummax().clip(lower=1.0)
    safe_peaks = peaks.replace(0, np.nan)
    dd_series = (wealth - safe_peaks) / safe_peaks
    underwater = ((safe_peaks - wealth) / safe_peaks) > 1e-5

    durations = []
    curr = 0
    for is_u in underwater:
        if is_u:
            curr += 1
        else:
            if curr > 0:
                durations.append(curr)
            curr = 0
    if curr > 0:
        durations.append(curr)

    max_days = max(durations) if durations else 0
    curr_days = curr if (not underwater.empty and bool(underwater.iloc[-1])) else 0
    curr_dd = float(dd_series.iloc[-1]) if not dd_series.empty else 0.0
    approx_months = max(1, round(max_days / 21)) if max_days >= 15 else 0

    return {
        "max_days": int(max_days),
        "curr_days": int(curr_days),
        "curr_dd": float(curr_dd),
        "approx_months": int(approx_months)
    }
