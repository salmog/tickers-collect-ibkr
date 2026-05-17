# MITLoop - IBKR Historical Data Engine

## Overview

This project collects and maintains a local historical OHLCV dataset from Interactive Brokers (IBKR) using IB Gateway API.

It is designed for:

- Large-scale multi-ticker data ingestion (~3000 tickers)
- Continuous historical updates (incremental fetch)
- Backtesting-ready dataset generation
- Resilient long-running execution on Ubuntu VM

---

## Data Architecture

### Timeframes

- 1H (direct from IBKR API)
- 4H (calculated locally from 1H data)
- Future: Daily / Weekly / Monthly

---

## Data Flow

IB Gateway (port 4001)
→ Python IBKR client (ib_insync)
→ Fetch 1H candles
→ Store CSV per ticker
→ Resample to 4H locally
→ Append-only updates
→ Resume from last timestamp

---

## Folder Structure
data/
1h/
4h/
state/
logs/
tickers.csv
main.py


---

## Features

- Incremental historical updates (no duplicate downloads)
- Automatic resume after crash or reboot
- Handles IBKR pacing limits safely
- Works with large ticker universe (3000+)
- Local resampling for higher timeframe generation
- Designed for always-on Ubuntu VM

---

## Requirements

- Ubuntu server
- IB Gateway running (API enabled)
- Python 3.10+
- ib_insync
- pandas

---

## IBKR Settings Required

- API enabled in IB Gateway
- Socket port: `4001`
- Read-only mode (recommended)
- Trusted IP: 127.0.0.1

---

## Notes

- IBKR does NOT provide native 4H bars → derived from 1H
- System is designed to respect IBKR pacing limits
- Data is stored locally as CSV for portability

---

## Future Extensions

- Database migration (PostgreSQL / DuckDB)
- Real-time streaming
- Feature engineering pipeline
- Trading strategy integration

2. Bootstrap project creator script

Create:

nano bootstrap_project.sh
Paste:
#!/bin/bash

BASE_DIR="fetch_candles_ibkr"

echo "Creating project structure..."

mkdir -p $BASE_DIR/data/1h
mkdir -p $BASE_DIR/data/4h
mkdir -p $BASE_DIR/state
mkdir -p $BASE_DIR/logs

touch $BASE_DIR/logs/runtime.log
touch $BASE_DIR/state/progress.json
touch $BASE_DIR/state/failed.json

# tickers
if [ ! -f "$BASE_DIR/tickers.csv" ]; then
    echo "tickers file missing - please copy manually"
fi

# python files
touch $BASE_DIR/main.py
touch $BASE_DIR/ib_client.py
touch $BASE_DIR/config.py

# requirements
cat > $BASE_DIR/requirements.txt << EOF
ib_insync
pandas
numpy
EOF

echo "Project structure created successfully."
echo "Next: activate venv + run main.py"

Make executable:

chmod +x bootstrap_project.sh

Run:

./bootstrap_project.sh
