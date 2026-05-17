# MITLoop - IBKR Historical Data Engine (v1.0)

## Overview
A highly resilient, continuous Python daemon that fetches and maintains historical OHLCV market data from Interactive Brokers (IBKR) via the IB Gateway API. Designed to run 24/7 on an Ubuntu VM, it effortlessly manages a massive dataset of thousands of tickers across multiple timeframes.

## Version 1.0 Features
* **Multi-Timeframe Fetching:** Pulls Monthly (10Y), Weekly (8Y), Daily (8Y), and Hourly (6M).
* **Local 4H Generation:** Automatically derives and saves 4-hour candles based on the 1-hour data.
* **Continuous Incremental Appending:** If data already exists, the script intelligently fetches only the missing recent candles and stitches them to the existing CSV without duplicates. 
* **Extended Hours & RTH Tagging:** Captures pre-market and after-hours data for intraday timeframes. Automatically calculates Wall Street time and tags every row with an `is_rth` (Regular Trading Hours) boolean.
* **Crash Resilience:** Auto-resumes exactly where it left off if the network drops or the Gateway disconnects.
* **Dynamic Routing:** Connect to the Gateway locally via `systemd` or remotely from a Mac using environment variables.

## Repository Structure
```text
├── main.py                # Main execution loop and file appending logic
├── ib_client.py           # IBKR API connection and timezone handling
├── requirements.txt       # Python dependencies
├── ibkr-fetch.service     # Ubuntu systemd service configuration
├── tickers2344.csv        # (User Provided) List of tickers to fetch
└── historical_data/       # Output directory for generated CSVs

_
Setup & Installation
Install dependencies:

Bash
pip install -r requirements.txt
Provide your tickers: Ensure your tickers2344.csv file is in the root directory.

Execution Models
Option A: Run Locally (Foreground)

Bash
python main.py
Option B: Run Remotely (e.g., from Mac to Ubuntu VM)

Bash
IB_GATEWAY_HOST=192.168.x.x IB_GATEWAY_PORT=4001 python main.py
Option C: Run as 24/7 Ubuntu Daemon

Bash
sudo cp ibkr-fetch.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start ibkr-fetch.service
sudo systemctl enable ibkr-fetch.service
Monitor live daemon logs: sudo journalctl -u ibkr-fetch.service -f


---

### 2. `main.py`

```python
import time
import random
import pandas as pd
import os
from ib_client import connect_ib, fetch_history

CSV_FILE = "tickers2344.csv"
DATA_DIR = "historical_data"

# Timeframes, durations, and whether to strict-filter Regular Trading Hours
CYCLES = {
    "monthly": {"duration": "10 Y", "inc_duration": "1 Y",  "bar_size": "1 month", "use_rth": True},
    "weekly":  {"duration": "8 Y",  "inc_duration": "3 M",  "bar_size": "1 week",  "use_rth": True},
    "daily":   {"duration": "8 Y",  "inc_duration": "1 M",  "bar_size": "1 day",   "use_rth": True},
    "hourly":  {"duration": "6 M",  "inc_duration": "10 D", "bar_size": "1 hour",  "use_rth": False} 
}

BASE_SLEEP = 3.0
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
        print("No tickers to process.")
        return

    print(f"🚀 Loaded {len(tickers)} tickers. Starting Appending loop...")
    ib = connect_ib()
    sleep_between = BASE_SLEEP

    for i, symbol in enumerate(tickers):
        for timeframe, params in CYCLES.items():
            filename = f"{DATA_DIR}/{symbol}_{timeframe}.csv"
            
            is_incremental = os.path.exists(filename)
            fetch_duration = params["inc_duration"] if is_incremental else params["duration"]

            delay = random.uniform(BASE_SLEEP, BASE_SLEEP + 2)
            time.sleep(delay)

            mode = "🔄 APPEND" if is_incremental else "📥 FULL FETCH"
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
                    print(f"⚠️ Corrupted existing file for {symbol} {timeframe}, overwriting. Error: {e}")
                    df = df_new
            else:
                df = df_new

            df.to_csv(filename, index=False)
            print(f"✅ SAVED {symbol} [{timeframe}] | Total Rows: {len(df)}")
            
            if timeframe == "hourly":
                try:
                    df_4h = df.copy()
                    df_4h.set_index('date', inplace=True)
                    
                    ohlcv_dict = {
                        'open': 'first',
                        'high': 'max',
                        'low': 'min',
                        'close': 'last',
                        'volume': 'sum',
                        'is_rth': 'max' 
                    }
                    ohlcv_dict = {k: v for k, v in ohlcv_dict.items() if k in df_4h.columns}
                    
                    df_4h = df_4h.resample('4h').agg(ohlcv_dict).dropna().reset_index()
                    
                    filename_4h = f"{DATA_DIR}/{symbol}_4h.csv"
                    df_4h.to_csv(filename_4h, index=False)
                    print(f"✅ GENERATED 4H for {symbol} | Rows: {len(df_4h)}")
                except Exception as e:
                    print(f"⚠️ Failed to generate 4H for {symbol}: {e}")

            sleep_between = max(BASE_SLEEP, sleep_between - 1.0)

    try:
        ib.disconnect()
    except Exception:
        pass

    print("🏁 DONE WITH ALL TICKERS. SLEEPING.")

def run_forever():
    while True:
        try:
            run_cycle()
            print("💤 Finished total sweep. Sleeping 12 hours before scanning for new candles...")
            time.sleep(43200) 
        except Exception as e:
            print(f"🔥 Critical cycle crash: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_forever()
3. ib_client.py
Python
from ib_insync import IB, Stock, util
import time
import random
import pandas as pd
import os

HOST = os.getenv("IB_GATEWAY_HOST", "127.0.0.1")
PORT = int(os.getenv("IB_GATEWAY_PORT", 4001))

def connect_ib():
    ib = IB()
    client_id = random.randint(10, 9999)
    print(f"🔌 Connecting IB on {HOST}:{PORT} clientId={client_id}")

    try:
        ib.connect(HOST, PORT, clientId=client_id, timeout=10, readonly=True)
        print("✅ IB CONNECTED")
        return ib
    except Exception as e:
        print(f"❌ IB connect failed on {HOST}:{PORT}: {e}")
        time.sleep(3)
        raise

def fetch_history(ib, symbol, duration, bar_size, use_rth=True):
    contract = Stock(symbol, "SMART", "USD")
    
    try:
        bars = ib.reqHistoricalData(
            contract,
            endDateTime="",
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=use_rth,  
            formatDate=2  
        )
        
        ib.sleep(1)

        if not bars:
            return None

        df = util.df(bars)
        
        first_date = str(df['date'].iloc[0])
        
        if first_date.isdigit() and len(first_date) >= 10:
            df['date'] = pd.to_datetime(df['date'], unit='s', utc=True)
        else:
            df['date'] = pd.to_datetime(df['date'], utc=True)
            
        # Tag RTH vs Pre/Post Market
        eastern_times = df['date'].dt.tz_convert('US/Eastern')
        is_after_open = (eastern_times.dt.hour > 9) | ((eastern_times.dt.hour == 9) & (eastern_times.dt.minute >= 30))
        is_before_close = (eastern_times.dt.hour < 16)
        df['is_rth'] = is_after_open & is_before_close

        return df

    except Exception as e:
        print(f"⚠️ Fetch error {symbol} ({bar_size}): {e}")
        return None
4. requirements.txt
Plaintext
ib_insync==0.9.86
pandas==2.2.2
5. ibkr-fetch.service
Ini, TOML
[Unit]
Description=IBKR Historical Data Fetcher
After=network.target

[Service]
User=shay
WorkingDirectory=/home/shay/autotrade_dev/fetch_candles_ibkr
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/shay/autotrade_dev/venv-ibkr/bin/python main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
Before we write the Docker compose file for the gateway, can you quickly check if Docker is already installed on your Ubuntu VM by running docker --version in your terminal?
