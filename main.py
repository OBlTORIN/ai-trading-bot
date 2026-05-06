from fastapi import FastAPI
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
    return {"status": "working"}

@app.get("/signal")
def signal(balance: float = 100):

    df = yf.download("GC=F", period="5d", interval="5m")

    if df.empty:
        return {"error": "No Data"}

    df = df.dropna()

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    close = df["Close"]

    # EMA

    ema9 = close.ewm(span=9).mean()
    ema21 = close.ewm(span=21).mean()

    # RSI

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    current_price = round(float(close.iloc[-1]), 1)

    current_rsi = float(rsi.iloc[-1])

    # SIGNAL LOGIC

    if ema9.iloc[-1] > ema21.iloc[-1] and current_rsi > 50:

        signal = "BUY"

        sl = round(current_price - 10, 1)

        tp = round(current_price + 20, 1)

        confidence = 88

    else:

        signal = "SELL"

        sl = round(current_price + 10, 1)

        tp = round(current_price - 20, 1)

        confidence = 86

    # RISK MANAGEMENT

    risk_amount = balance * 0.02

    sl_distance = abs(current_price - sl)

    lot_size = round(risk_amount / (sl_distance * 10), 2)

    tp_profit = round(abs(tp - current_price) * lot_size * 10, 2)

    sl_loss = round(abs(sl - current_price) * lot_size * 10, 2)

    return {

        "signal": signal,
        "entry": current_price,
        "sl": sl,
        "tp": tp,
        "lot": lot_size,
        "profit": tp_profit,
        "loss": sl_loss,
        "confidence": f"{confidence}%"

    }
