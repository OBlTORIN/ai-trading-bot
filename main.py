from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    ema50 = close.ewm(span=50).mean()

    # RSI

    delta = close.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    rsi = 100 - (100 / (1 + rs))

    current_price = round(float(close.iloc[-1]), 1)

    current_rsi = round(float(rsi.iloc[-1]), 1)

    ema9_now = float(ema9.iloc[-1])
    ema21_now = float(ema21.iloc[-1])
    ema50_now = float(ema50.iloc[-1])

    # TREND

    if current_price > ema50_now:
        trend = "UPTREND"

    else:
        trend = "DOWNTREND"

    # SIGNAL LOGIC

    if ema9_now > ema21_now and current_rsi > 55:

        signal = "BUY"

        sl = round(current_price - 10, 1)

        tp = round(current_price + 20, 1)

        confidence = 90

    elif ema9_now < ema21_now and current_rsi < 45:

        signal = "SELL"

        sl = round(current_price + 10, 1)

        tp = round(current_price - 20, 1)

        confidence = 88

    else:

        signal = "WAIT"

        sl = current_price
        tp = current_price

        confidence = 50

    # RISK MANAGEMENT

    risk_percent = 0.02

    risk_amount = balance * risk_percent

    sl_distance = abs(current_price - sl)

    if sl_distance == 0:
        lot_size = 0
    else:
        lot_size = round(risk_amount / (sl_distance * 10), 2)

    tp_profit = round(abs(tp - current_price) * lot_size * 10, 2)

    sl_loss = round(abs(sl - current_price) * lot_size * 10, 2)

    # MARKET STRENGTH

    if confidence >= 90:
        strength = "VERY STRONG"

    elif confidence >= 80:
        strength = "STRONG"

    elif confidence >= 70:
        strength = "MODERATE"

    else:
        strength = "WEAK"

    return {

        "signal": signal,
        "entry": current_price,
        "sl": sl,
        "tp": tp,
        "lot": lot_size,
        "profit": tp_profit,
        "loss": sl_loss,
        "confidence": f"{confidence}%",
        "trend": trend,
        "strength": strength,
        "rsi": current_rsi

    }
