from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import yfinance as yf
import pandas as pd

app = FastAPI()

# CORS FIX
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# FRONTEND OPEN
@app.get("/")
def home():
    return FileResponse("index.html")

# SIGNAL API
@app.get("/signal")
def signal():

    try:

        df = yf.download("GC=F", period="5d", interval="1h")

        if df.empty:
            return {"error": "No data"}

        df = df.dropna()

        # FIX MULTI INDEX
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = float(df["Close"].iloc[-1])

        signal_type = "BUY"

        entry = round(close, 1)
        sl = round(close - 10, 1)
        tp = round(close + 20, 1)

        return {
            "signal": signal_type,
            "entry": entry,
            "sl": sl,
            "tp": tp,
            "confidence": "65%"
        }

    except Exception as e:
        return {"error": str(e)}
