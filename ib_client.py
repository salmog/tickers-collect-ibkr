from ib_insync import IB, Stock, util
import time
import random
import pandas as pd
import os

# 🔥 NEW: Read from environment variables, fallback to localhost if not set
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
