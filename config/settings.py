# config/settings.py
import os
from pathlib import Path


RISK_FREE_RATE: float = float(os.getenv("RISK_FREE_RATE", "0.0705"))
TRADING_DAYS_PER_YEAR: int = 252
BENCHMARK_TICKER: str = "^NSEI"  

# 2. Tracked NSE Equity Universe (Diverse Large-Caps across 7 sectors)
TRACKED_TICKERS: list[str] = [
    # Information Technology
    "TCS.NS",
    "INFY.NS",
    # Financial Services & Banking
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BAJFINANCE.NS",
    # Energy, Oil & Utilities
    "RELIANCE.NS",
    "NTPC.NS",
    # FMCG & Consumption
    "ITC.NS",
    "HINDUNILVR.NS",
    "TITAN.NS",
    # Auto & Manufacturing
    "M&M.NS",
    "MARUTI.NS",
    # Healthcare & Pharma
    "SUNPHARMA.NS",
    # Infrastructure, Materials & Industrial
    "LT.NS",
    "TATASTEEL.NS",
]

# 3. Database Connection URI
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_DB_PATH = (BASE_DIR / ".." / "data" / "screener.db").resolve()
DB_PATH = os.getenv("DB_PATH", str(DEFAULT_DB_PATH))