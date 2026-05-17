import time
from ib_insync import IB


def connect_ib(host, port, client_id):
    ib = IB()

    while True:
        try:
            ib.connect(host, port, clientId=client_id)

            ib.reqMarketDataType(1)

            print("✅ IB CONNECTED")
            return ib

        except Exception as e:
            print("❌ IB reconnect failed, retrying...", e)
            time.sleep(5)


def ensure_connection(ib):
    try:
        if ib.isConnected():
            return ib
    except:
        pass

    print("⚠️ IB DISCONNECTED → reconnecting...")

    try:
        ib.disconnect()
    except:
        pass

    return connect_ib("127.0.0.1", 4001, 7)
