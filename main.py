from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import yfinance as yf
import pandas as pd
import json
import os

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
# MEMORY FILE
# =========================

MEMORY_FILE = "memory.json"

if not os.path.exists(MEMORY_FILE):

    with open(MEMORY_FILE, "w") as f:

        json.dump({

            "wins": 0,
            "losses": 0,
            "total": 0

        }, f)


# =========================
# LOAD MEMORY
# =========================

def load_memory():

    with open(MEMORY_FILE, "r") as f:

        return json.load(f)


# =========================
# SAVE MEMORY
# =========================

def save_memory(data):

    with open(MEMORY_FILE, "w") as f:

        json.dump(data, f)


# =========================
# ANALYSIS
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

    high = df["High"]

    low = df["Low"]

    open_price = df["Open"]

    # EMA

    ema20 = close.ewm(span=20).mean()

    ema50 = close.ewm(span=50).mean()

    # RSI

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

    # SUPPORT / RESISTANCE

    support = round(
        float(low.tail(20).min()),
        1
    )

    resistance = round(
        float(high.tail(20).max()),
        1
    )

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

    # BREAKOUT

    breakout = False

    if current_price > resistance:

        breakout = True

        signal = "BUY"

    if current_price < support:

        breakout = True

        signal = "SELL"

    # CANDLE STRENGTH

    candle_body = abs(
        close.iloc[-1] - open_price.iloc[-1]
    )

    candle_range = (
        high.iloc[-1] - low.iloc[-1]
    )

    candle_strength = 0

    if candle_range > 0:

        candle_strength = round(
            (candle_body / candle_range) * 100,
            1
        )

    return {

        "signal": signal,

        "price": current_price,

        "support": support,

        "resistance": resistance,

        "breakout": breakout,

        "candle_strength": candle_strength

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

    support = tf5["support"]

    resistance = tf5["resistance"]

    breakout = tf5["breakout"]

    candle_strength = tf5["candle_strength"]

    confidence = 60

    # FINAL SIGNAL

    if buy_count >= 2:

        final_signal = "BUY"

        sl = support

        tp = round(
            current_price +
            ((current_price - sl) * 2),
            1
        )

        confidence += 15

    elif sell_count >= 2:

        final_signal = "SELL"

        sl = resistance

        tp = round(
            current_price -
            ((sl - current_price) * 2),
            1
        )

        confidence += 15

    else:

        final_signal = "WAIT"

        sl = current_price

        tp = current_price

    # BREAKOUT BONUS

    if breakout:

        confidence += 10

    # STRONG CANDLE BONUS

    if candle_strength > 70:

        confidence += 10

    if confidence > 95:

        confidence = 95

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

    # =========================
    # MEMORY STATS
    # =========================

    memory = load_memory()

    total = memory["total"]

    wins = memory["wins"]

    losses = memory["losses"]

    if total > 0:

        win_rate = round(
            (wins / total) * 100,
            1
        )

    else:

        win_rate = 0

    return {

        "signal": final_signal,

        "entry": current_price,

        "sl": sl,

        "tp": tp,

        "lot": lot,

        "profit": profit,

        "loss": loss,

        "confidence": f"{confidence}%",

        "total_trades": total,

        "wins": wins,

        "losses": losses,

        "win_rate": f"{win_rate}%"

    }


# =========================
# MANUAL RESULT UPDATE
# =========================

@app.get("/update_result")
def update_result(result: str):

    memory = load_memory()

    memory["total"] += 1

    if result == "win":

        memory["wins"] += 1

    elif result == "loss":

        memory["losses"] += 1

    save_memory(memory)

    return {

        "message": "updated",

        "memory": memory

    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
