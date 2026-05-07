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


@app.get("/signal")
def signal(balance: float = 100):

    # REAL XAUUSD DATA

    df = yf.download(
        "GC=F",
        period="5d",
        interval="5m"
    )

    if df.empty:
        return {
            "error": "No Market Data"
        }

    df = df.dropna()

    # FIX COLUMNS

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"]

    # REAL EMA

    ema20 = close.ewm(span=20).mean()

    ema50 = close.ewm(span=50).mean()

    # REAL RSI

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    # CURRENT VALUES

    current_price = round(
        float(close.iloc[-1]),
        1
    )

    current_ema20 = round(
        float(ema20.iloc[-1]),
        1
    )

    current_ema50 = round(
        float(ema50.iloc[-1]),
        1
    )

    current_rsi = round(
        float(rsi.iloc[-1]),
        1
    )

    # SUPPORT / RESISTANCE

    support = round(
        float(df["Low"].tail(20).min()),
        1
    )

    resistance = round(
        float(df["High"].tail(20).max()),
        1
    )

    # TREND

    if current_ema20 > current_ema50:
        trend = "BUY"
    else:
        trend = "SELL"

    # SIGNAL LOGIC

    if current_rsi > 70:

        signal = "SELL"

    elif current_rsi < 35:

        signal = "BUY"

    else:

        signal = trend

    # ENTRY / SL / TP

    entry = current_price

    if signal == "BUY":

        sl = support

        tp = round(
            entry + ((entry - sl) * 2),
            1
        )

    else:

        sl = resistance

        tp = round(
            entry - ((sl - entry) * 2),
            1
        )

    # LOT SIZE

    risk_amount = balance * 0.02

    sl_distance = abs(entry - sl)

    if sl_distance == 0:
        sl_distance = 1

    lot = round(
        risk_amount / (sl_distance * 10),
        2
    )

    if lot < 0.01:
        lot = 0.01

    # PROFIT / LOSS

    profit = round(
        abs(tp - entry) * lot * 10,
        2
    )

    loss = round(
        abs(sl - entry) * lot * 10,
        2
    )

    # CONFIDENCE

    confidence = 60

    if trend == signal:
        confidence += 10

    if current_rsi < 35 or current_rsi > 70:
        confidence += 10

    if abs(current_ema20 - current_ema50) > 3:
        confidence += 10

    if confidence > 95:
        confidence = 95

    return {

        "signal": signal,

        "entry": entry,

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
