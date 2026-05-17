import time
import random
import pandas as pd
import os
from ib_client import connect_ib, fetch_history

CSV_FILE = "tickers2344.csv"
DATA_DIR = "historical_data"

CYCLES = {
    "monthly": {"duration": "10 Y", "inc_duration": "1 Y",  "bar_size": "1 month", "use_rth": True},
    "weekly":  {"duration": "8 Y",  "inc_duration": "3 M",  "bar_size": "1 week",  "use_rth": True},
    "daily":   {"duration": "8 Y",  "inc_duration": "1 M",  "bar_size": "1 day",   "use_rth": True},
    "hourly":  {"duration": "6 M",  "inc_duration": "10 D", "bar_size": "1 hour",  "use_rth": False} 
}

# 🔥 FIX 3: Increased Speed (Lower sleep time)
BASE_SLEEP = 1.5
MAX_SLEEP = 15.0

def load_tickers(filepath):
    if not os.path.exists(filepath):
        print(f"❌ {filepath} not found. Please provide the CSV.")
        return []
        
    df = pd.read_csv(filepath)
    if 'ticker' in df.columns:
        return df['ticker'].dropna().astype(str).unique().tolist()
    else:
        return df.iloc[:, 0].dropna().astype(str).unique().tolist()

def run_cycle():
    os.makedirs(DATA_DIR, exist_ok=True)
    tickers = load_tickers(CSV_FILE)
    
    if not tickers:
        return

    print(f"🚀 Loaded {len(tickers)} tickers. Starting loop...")
    ib = connect_ib()
    sleep_between = BASE_SLEEP

    for i, symbol in enumerate(tickers):
        for timeframe, params in CYCLES.items():
            filename = f"{DATA_DIR}/{symbol}_{timeframe}.csv"
            
            is_incremental = False
            
            # 🔥 FIX 2: Fast-Forward logic. Skip if updated in the last 12 hours.
            if os.path.exists(filename):
                last_modified = os.path.getmtime(filename)
                if (time.time() - last_modified) < 43200: # 43200 seconds = 12 hours
                    print(f"⏭️ SKIP {symbol} [{timeframe}] - Updated recently")
                    continue
                is_incremental = True
                
            fetch_duration = params["inc_duration"] if is_incremental else params["duration"]

            delay = random.uniform(BASE_SLEEP, BASE_SLEEP + 1)
            time.sleep(delay)

            mode = "🔄 APPEND" if is_incremental else "📥 FETCH"
            print(f"[{i+1}/{len(tickers)}] {mode} {symbol} - {timeframe}")
            
            df_new = fetch_history(ib, symbol, fetch_duration, params["bar_size"], params["use_rth"])

            if df_new is None or len(df_new) == 0:
                sleep_between = min(sleep_between + 3, MAX_SLEEP)
                print(f"⚠️ Empty/Error {symbol} [{timeframe}] → backoff {sleep_between:.1f}s")
                time.sleep(sleep_between)
                continue

            if is_incremental:
                try:
                    df_existing = pd.read_csv(filename)
                    df_existing['date'] = pd.to_datetime(df_existing['date'], utc=True)
                    df_new['date'] = pd.to_datetime(df_new['date'], utc=True)
                    
                    df_combined = pd.concat([df_existing, df_new])
                    df_combined = df_combined.drop_duplicates(subset=['date'], keep='last').sort_values('date')
                    df = df_combined
                except Exception as e:
                    print(f"⚠️ Corrupted existing file {symbol}, overwriting: {e}")
                    df = df_new
            else:
                df = df_new

            df.to_csv(filename, index=False)
            print(f"✅ SAVED {symbol} [{timeframe}] | Total Rows: {len(df)}")
            
            if timeframe == "hourly":
                try:
                    df_4h = df.copy()
                    df_4h.set_index('date', inplace=True)
                    
                    ohlcv_dict = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum', 'is_rth': 'max'}
                    ohlcv_dict = {k: v for k, v in ohlcv_dict.items() if k in df_4h.columns}
                    
                    df_4h = df_4h.resample('4h').agg(ohlcv_dict).dropna().reset_index()
                    df_4h.to_csv(f"{DATA_DIR}/{symbol}_4h.csv", index=False)
                except Exception as e:
                    print(f"⚠️ Failed 4H for {symbol}: {e}")

            sleep_between = max(BASE_SLEEP, sleep_between - 0.5)

    try:
        ib.disconnect()
    except Exception:
        pass

def run_forever():
    while True:
        try:
            run_cycle()
            print("💤 Finished sweep. Sleeping 12 hours...")
            time.sleep(43200) 
        except Exception as e:
            print(f"🔥 Critical cycle crash: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_forever()
