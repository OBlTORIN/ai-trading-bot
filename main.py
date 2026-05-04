from fastapi import FastAPI
import yfinance as yf
import pandas as pd

app = FastAPI()

@app.get("/")
def home():
    return {"status": "working"}

@app.get("/signal")
def signal():
    try:
        df = yf.download("GC=F", period="5d", interval="1h")

        if df.empty:
            return {"error": "No data"}

        df = df.dropna()

        # FIX: ensure single column (important)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df['EMA50'] = df['Close'].ewm(span=50).mean()
        df['EMA200'] = df['Close'].ewm(span=200).mean()

        # FIX: use iloc properly
        close = df['Close'].iloc[-1]
        ema50 = df['EMA50'].iloc[-1]
        ema200 = df['EMA200'].iloc[-1]

        if pd.isna(close) or pd.isna(ema50) or pd.isna(ema200):
            return {"error": "NaN values"}

        if ema50 > ema200:
            signal = "BUY"
            sl = close - 10
            tp = close + 20
        else:
            signal = "SELL"
            sl = close + 10
            tp = close - 20

        return {
            "signal": signal,
            "entry": round(float(close), 2),
            "sl": round(float(sl), 2),
            "tp": round(float(tp), 2),
            "confidence": "65%"
        }

    except Exception as e:
        return {"error": str(e)}