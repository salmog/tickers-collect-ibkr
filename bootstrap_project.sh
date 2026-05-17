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
