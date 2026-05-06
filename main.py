from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import yfinance as yf
import pandas as pd
import numpy as np

app = FastAPI()

# =========================
# CORS
# =========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# HOME
# =========================

@app.get("/")
def home():

    return {
        "status": "working"
    }

# =========================
# SIGNAL
# =========================

@app.get("/signal")
def signal():

    try:

        # =========================
        # DOWNLOAD XAUUSD DATA
        # =========================

        df = yf.download(
            "GC=F",
            period="7d",
            interval="5m"
        )

        df = df.dropna()

        # FIX MULTI INDEX

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # =========================
        # EMA
        # =========================

        df["EMA9"] = (
            df["Close"]
            .ewm(span=9, adjust=False)
            .mean()
        )

        df["EMA21"] = (
            df["Close"]
            .ewm(span=21, adjust=False)
            .mean()
        )

        df["EMA50"] = (
            df["Close"]
            .ewm(span=50, adjust=False)
            .mean()
        )

        # =========================
        # RSI
        # =========================

        delta = df["Close"].diff()

        gain = (
            delta.where(delta > 0, 0)
            .rolling(14)
            .mean()
        )

        loss = (
            -delta.where(delta < 0, 0)
            .rolling(14)
            .mean()
        )

        rs = gain / loss

        df["RSI"] = (
            100 - (100 / (1 + rs))
        )

        # =========================
        # MACD
        # =========================

        ema12 = (
            df["Close"]
            .ewm(span=12, adjust=False)
            .mean()
        )

        ema26 = (
            df["Close"]
            .ewm(span=26, adjust=False)
            .mean()
        )

        df["MACD"] = ema12 - ema26

        df["Signal_Line"] = (
            df["MACD"]
            .ewm(span=9, adjust=False)
            .mean()
        )

        # =========================
        # SUPPORT RESISTANCE
        # =========================

        support = round(
            df["Low"].tail(30).min(),
            1
        )

        resistance = round(
            df["High"].tail(30).max(),
            1
        )

        # =========================
        # VOLUME
        # =========================

        avg_volume = (
            df["Volume"]
            .tail(20)
            .mean()
        )

        current_volume = (
            df["Volume"]
            .iloc[-1]
        )

        volume_strength = (
            current_volume > avg_volume
        )

        # =========================
        # LAST CANDLE
        # =========================

        last = df.iloc[-1]

        entry = round(last["Close"], 1)

        signal = "WAIT"

        confidence = 50

        sl = entry
        tp = entry

        # =========================
        # BUY CONDITIONS
        # =========================

        buy_score = 0

        if last["EMA9"] > last["EMA21"]:
            buy_score += 1

        if last["EMA21"] > last["EMA50"]:
            buy_score += 1

        if last["RSI"] > 55:
            buy_score += 1

        if last["MACD"] > last["Signal_Line"]:
            buy_score += 1

        if volume_strength:
            buy_score += 1

        # =========================
        # SELL CONDITIONS
        # =========================

        sell_score = 0

        if last["EMA9"] < last["EMA21"]:
            sell_score += 1

        if last["EMA21"] < last["EMA50"]:
            sell_score += 1

        if last["RSI"] < 45:
            sell_score += 1

        if last["MACD"] < last["Signal_Line"]:
            sell_score += 1

        if volume_strength:
            sell_score += 1

        # =========================
        # FINAL DECISION
        # =========================

        if buy_score >= 4:

            signal = "BUY"

            sl = round(
                support - 2,
                1
            )

            tp = round(
                entry + ((entry - sl) * 2),
                1
            )

            confidence = (
                70 + (buy_score * 5)
            )

        elif sell_score >= 4:

            signal = "SELL"

            sl = round(
                resistance + 2,
                1
            )

            tp = round(
                entry - ((sl - entry) * 2),
                1
            )

            confidence = (
                70 + (sell_score * 5)
            )

        else:

            signal = "WAIT"

            sl = round(entry - 5, 1)

            tp = round(entry + 5, 1)

            confidence = 55

        # =========================
        # RETURN
        # =========================

        return {

            "signal": signal,

            "entry": entry,

            "sl": sl,

            "tp": tp,

            "confidence": f"{confidence}%",

            "ema9": round(last["EMA9"], 1),

            "ema21": round(last["EMA21"], 1),

            "ema50": round(last["EMA50"], 1),

            "rsi": round(last["RSI"], 1),

            "macd": round(last["MACD"], 2),

            "support": support,

            "resistance": resistance,

            "volume_strength": bool(volume_strength),

            "buy_score": buy_score,

            "sell_score": sell_score

        }

    except Exception as e:

        return {
            "error": str(e)
        }
