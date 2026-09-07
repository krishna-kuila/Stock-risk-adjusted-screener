import sqlite3
import yfinance as yf
import pandas as pd
from config import TRACKED_TICKERS, BENCHMARK_TICKER, DB_PATH

def run_etl():
    all_symbols = TRACKED_TICKERS + [BENCHMARK_TICKER]
    raw = yf.download(all_symbols, period="5y", interval="1d", auto_adjust=False, group_by="ticker", progress=True)
    
    bench_clean = raw[BENCHMARK_TICKER].dropna(subset=["Adj Close"])
    valid_dates = set(pd.to_datetime(bench_clean.index).strftime("%Y-%m-%d"))

    frames = []
    for ticker in all_symbols:
        df = raw[ticker].copy().reset_index()
        df.rename(columns={"Date": "date", "Open": "open", "High": "high", "Low": "low", 
                           "Close": "close", "Adj Close": "adj_close", "Volume": "volume"}, inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df = df[df["date"].isin(valid_dates)].sort_values("date").reset_index(drop=True)
        df["adj_close"] = df["adj_close"].ffill()
        df["daily_return"] = df["adj_close"].pct_change()
        df["ticker"] = ticker
        frames.append(df.dropna(subset=["daily_return"]))

    master = pd.concat(frames, ignore_index=True)
    conn = sqlite3.connect(DB_PATH)
    master.to_sql("stock_prices", conn, if_exists="replace", index=False)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ticker_date ON stock_prices(ticker, date);")
    conn.commit()
    conn.close()
    print(f"ETL Complete: Saved {len(master)} rows to {DB_PATH}")

if __name__ == "__main__":
    run_etl()