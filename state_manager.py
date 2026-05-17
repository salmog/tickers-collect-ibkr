import os
import json

STATE_FILE = "state/progress.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    os.makedirs("state", exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_last_timestamp(state, symbol, timeframe):
    return state.get(symbol, {}).get(timeframe)

def update_state(state, symbol, timeframe, last_ts):
    if symbol not in state:
        state[symbol] = {}
    state[symbol][timeframe] = last_ts
