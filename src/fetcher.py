import concurrent.futures
import urllib.parse
from typing import Optional, Set, Union
import yfinance as yf
import pandas as pd
from curl_cffi import requests


# Well-known Indian stock ticker aliases, company names, and rebrands
TICKER_ALIASES: dict[str, str] = {
    # Reliance variations
    "RIL": "RELIANCE",
    "RELIANCE": "RELIANCE",
    "RELIANCE INDUSTRIES": "RELIANCE",
    "RELIANCE IND": "RELIANCE",
    "RELIANCE INDUSTRY": "RELIANCE",
    "RELIANCE STOCK": "RELIANCE",
    "RELIANCE POWER": "RPOWER",
    "RELIANCE INFRA": "RELINFRA",
    # Banking & Financial Services
    "SBI": "SBIN",
    "STATE BANK": "SBIN",
    "STATE BANK OF INDIA": "SBIN",
    "HDFC": "HDFCBANK",
    "HDFC BANK": "HDFCBANK",
    "ICICI": "ICICIBANK",
    "ICICI BANK": "ICICIBANK",
    "KOTAK": "KOTAKBANK",
    "KOTAK BANK": "KOTAKBANK",
    "AXIS": "AXISBANK",
    "AXIS BANK": "AXISBANK",
    "BAJAJ FINANCE": "BAJFINANCE",
    "BAJAJFINANCE": "BAJFINANCE",
    "BAJAJ FINSERV": "BAJAJFINSV",
    # Information Technology
    "TCS": "TCS",
    "TATA CONSULTANCY": "TCS",
    "INFY": "INFY",
    "INFOSYS": "INFY",
    "WIPRO": "WIPRO",
    "HCLTECH": "HCLTECH",
    "HCL TECH": "HCLTECH",
    "MINDTREE": "LTIM",
    "LTI": "LTIM",
    # Industrial, Auto & Materials
    "L&T": "LT",
    "LARSEN": "LT",
    "LARSEN & TOUBRO": "LT",
    "LARSEN AND TOUBRO": "LT",
    "TATA STEEL": "TATASTEEL",
    "TATA MOTORS": "TMPV",
    "TATAMOTORS": "TMPV",
    "TATAMOTOR": "TMPV",
    "TMPV": "TMPV",
    "TMLCV": "TMLCV",
    "TATA POWER": "TATAPOWER",
    "MARUTI SUZUKI": "MARUTI",
    "MARUTI": "MARUTI",
    "MAHINDRA": "M&M",
    "MAHINDRA & MAHINDRA": "M&M",
    # FMCG, Pharma & Telecom
    "HUL": "HINDUNILVR",
    "HINDUSTAN UNILEVER": "HINDUNILVR",
    "ITC": "ITC",
    "SUN PHARMA": "SUNPHARMA",
    "SUNPHARMA": "SUNPHARMA",
    "CADILAHC": "ZYDUSLIFE",
    "MOTHERSUMI": "MOTHERSON",
    "ZOMATO": "ETERNAL",
    "BHARTI AIRTEL": "BHARTIARTL",
    "AIRTEL": "BHARTIARTL",
}


def _fetch_direct_chart(sym: str, period: str = "5y", timeout: float = 3.5) -> tuple[int, Optional[pd.Series], str]:
    """
    Directly queries Yahoo Finance's v8 chart API with browser impersonation and fast timeout.
    Returns:
      (status_code: int, returns: Optional[pd.Series], info_or_err: str)
    """
    quoted = urllib.parse.quote(sym)
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{quoted}?range={period}&interval=1d"
    try:
        r = requests.get(url, impersonate="chrome", timeout=timeout)
        if r.status_code == 200:
            data = r.json()
            res = data.get("chart", {}).get("result")
            if res:
                chart = res[0]
                timestamps = chart.get("timestamp", [])
                if timestamps:
                    ind = chart.get("indicators", {})
                    adj = None
                    if "adjclose" in ind and ind["adjclose"] and "adjclose" in ind["adjclose"][0]:
                        adj = ind["adjclose"][0]["adjclose"]
                    if not adj and "quote" in ind and ind["quote"] and "close" in ind["quote"][0]:
                        adj = ind["quote"][0]["close"]
                    if adj:
                        dates = pd.to_datetime(timestamps, unit="s").strftime("%Y-%m-%d")
                        s = pd.Series(adj, index=dates).dropna()
                        if len(s) >= 30:
                            s = s.ffill()
                            ret = s.pct_change().dropna()
                            ret.name = sym
                            return 200, ret, "OK"
            return 200, None, "EMPTY_DATA"
        elif r.status_code == 404:
            return 404, None, "NOT_FOUND"
        else:
            return r.status_code, None, f"HTTP_{r.status_code}"
    except Exception as e:
        return 0, None, str(e)


def fetch_stock_returns(
    ticker: str,
    period: str = "5y",
    valid_dates: Optional[Union[Set[str], list, pd.Index]] = None,
    min_days: int = 30
) -> tuple[bool, Optional[pd.Series], str]:
    """
    Fetches daily returns for a stock on-demand with high-performance 2-tier live retrieval:
      Tier 1: Direct v8 JSON chart API with parallel candidate lookup (sub-2s resolution)
      Tier 2: yfinance fallback only if network/SSL error occurred (not for 404 Not Found)
    """
    raw_input = ticker.strip().upper() if ticker else ""
    if not raw_input:
        return False, None, "Empty ticker symbol provided."

    # Normalize whitespace
    norm_ticker = " ".join(raw_input.split())
    base_sym = norm_ticker
    suffix = ""
    for sfx in [".NS", ".BO"]:
        if norm_ticker.endswith(sfx):
            base_sym = norm_ticker[:-len(sfx)].strip()
            suffix = sfx
            break

    compact_sym = base_sym.replace(" ", "").replace("-", "")

    # Build prioritized list of candidate symbols
    candidates = []
    # 1. Alias match on raw base name
    if base_sym in TICKER_ALIASES:
        target = TICKER_ALIASES[base_sym]
        candidates.extend([f"{target}.NS", f"{target}.BO", target])

    # 2. Alias match on compact name (no spaces)
    if compact_sym in TICKER_ALIASES and compact_sym != base_sym:
        target = TICKER_ALIASES[compact_sym]
        candidates.extend([f"{target}.NS", f"{target}.BO", target])

    # 3. Standard symbol variations
    if suffix:
        candidates.append(f"{base_sym}{suffix}")
        candidates.append(f"{compact_sym}{suffix}")
    elif not norm_ticker.startswith("^"):
        candidates.extend([f"{compact_sym}.NS", f"{base_sym}.NS", f"{base_sym}.BO", compact_sym, base_sym])
    else:
        candidates.append(norm_ticker)

    # Deduplicate while preserving order and filtering out symbols with spaces
    seen = set()
    ordered_candidates = [
        c for c in candidates 
        if c and (" " not in c) and not (c in seen or seen.add(c))
    ]

    # -------------------------------------------------------------
    # Tier 1: Fast Parallel Validation & Retrieval via Direct v8 Chart API
    # -------------------------------------------------------------
    direct_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(ordered_candidates), 3)) as executor:
        future_to_sym = {
            executor.submit(_fetch_direct_chart, sym, period, 3.5): sym
            for sym in ordered_candidates
        }
        for future in concurrent.futures.as_completed(future_to_sym):
            sym = future_to_sym[future]
            try:
                direct_results[sym] = future.result()
            except Exception as e:
                direct_results[sym] = (0, None, str(e))

    # Check candidates in original prioritized order (e.g. .NS first)
    all_not_found = True
    for sym in ordered_candidates:
        status, ret, _ = direct_results.get(sym, (0, None, "NOT_RUN"))
        if status == 200 and ret is not None and len(ret) >= min_days:
            if valid_dates is not None:
                valid_set = set(valid_dates)
                ret = ret[ret.index.isin(valid_set)]
            if len(ret) >= min_days:
                return True, ret, f"Successfully loaded {len(ret)} trading days for '{sym}'."
        if status != 404:
            all_not_found = False

    # If all candidate symbols returned 404 (Not Found), abort immediately (sub-2s)
    # without slow multi-request cookie retry cycles
    if all_not_found:
        return False, None, f"Could not find live market data for '{raw_input}'. Please check the symbol."

    # -------------------------------------------------------------
    # Tier 2: Fallback to yfinance if direct API had network/SSL/timeout issue
    # -------------------------------------------------------------
    retry_candidates = [
        sym for sym in ordered_candidates 
        if direct_results.get(sym, (0, None, ""))[0] != 404
    ]

    for sym in retry_candidates:
        try:
            t = yf.Ticker(sym)
            h = t.history(period=period, interval="1d", auto_adjust=False)
            if not h.empty and len(h) >= min_days:
                close = h["Close"].dropna() if "Close" in h.columns else (h["Adj Close"].dropna() if "Adj Close" in h.columns else None)
                if close is not None and len(close) >= min_days:
                    close = close.ffill()
                    returns = close.pct_change().dropna()
                    returns.index = pd.to_datetime(returns.index).strftime("%Y-%m-%d")
                    returns.name = sym
                    if valid_dates is not None:
                        valid_set = set(valid_dates)
                        returns = returns[returns.index.isin(valid_set)]
                    if len(returns) >= min_days:
                        return True, returns, f"Successfully loaded {len(returns)} trading days for '{sym}'."
        except Exception:
            continue

    return False, None, f"Could not find live market data for '{raw_input}'. Please check the symbol."
