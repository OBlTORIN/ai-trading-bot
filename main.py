from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import yfinance as yf
import pandas as pd

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():

    return FileResponse("index.html")


# =========================
# ANALYSIS FUNCTION
# =========================

def analyze_timeframe(interval):

    df = yf.download(
        "GC=F",
        period="5d",
        interval=interval
    )

    df = df.dropna()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"]

    ema20 = close.ewm(span=20).mean()

    ema50 = close.ewm(span=50).mean()

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    current_price = round(
        float(close.iloc[-1]),
        1
    )

    current_ema20 = float(ema20.iloc[-1])

    current_ema50 = float(ema50.iloc[-1])

    current_rsi = float(rsi.iloc[-1])

    # TREND

    if current_ema20 > current_ema50:
        trend = "BUY"
    else:
        trend = "SELL"

    # RSI FILTER

    if current_rsi > 70:
        signal = "SELL"

    elif current_rsi < 35:
        signal = "BUY"

    else:
        signal = trend

    return {
        "signal": signal,
        "price": current_price,
        "rsi": round(current_rsi,1)
    }


# =========================
# MAIN SIGNAL
# =========================

@app.get("/signal")
def signal(balance: float = 100):

    tf1 = analyze_timeframe("1m")

    tf5 = analyze_timeframe("5m")

    tf15 = analyze_timeframe("15m")

    signals = [
        tf1["signal"],
        tf5["signal"],
        tf15["signal"]
    ]

    buy_count = signals.count("BUY")

    sell_count = signals.count("SELL")

    current_price = tf5["price"]

    # FINAL DECISION

    if buy_count >= 2:

        final_signal = "BUY"

        sl = round(current_price - 10,1)

        tp = round(current_price + 20,1)

        confidence = 85 + (buy_count * 3)

    elif sell_count >= 2:

        final_signal = "SELL"

        sl = round(current_price + 10,1)

        tp = round(current_price - 20,1)

        confidence = 85 + (sell_count * 3)

    else:

        final_signal = "WAIT"

        sl = current_price

        tp = current_price

        confidence = 50

    # LOT SIZE

    risk_amount = balance * 0.02

    sl_distance = abs(current_price - sl)

    if sl_distance == 0:
        sl_distance = 1

    lot = round(
        risk_amount / (sl_distance * 10),
        2
    )

    if lot < 0.01:
        lot = 0.01

    # PROFIT LOSS

    profit = round(
        abs(tp - current_price) * lot * 10,
        2
    )

    loss = round(
        abs(sl - current_price) * lot * 10,
        2
    )

    return {

        "signal": final_signal,

        "entry": current_price,

        "sl": sl,

        "tp": tp,

        "lot": lot,

        "profit": profit,

        "loss": loss,

        "confidence": f"{confidence}%"

    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
