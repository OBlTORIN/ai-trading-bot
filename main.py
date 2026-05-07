from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import yfinance as yf
import pandas as pd
import numpy as np

from sklearn.ensemble import RandomForestClassifier

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


def load_memory():

    with open(MEMORY_FILE, "r") as f:

        return json.load(f)


def save_memory(data):

    with open(MEMORY_FILE, "w") as f:

        json.dump(data, f)


# =========================
# DOWNLOAD DATA
# =========================

def get_data():

    df = yf.download(
        "GC=F",
        period="30d",
        interval="5m"
    )

    df = df.dropna()

    if isinstance(df.columns, pd.MultiIndex):

        df.columns = df.columns.get_level_values(0)

    return df


# =========================
# ADD FEATURES
# =========================

def add_features(df):

    close = df["Close"]

    # EMA

    df["EMA20"] = (
        close.ewm(span=20).mean()
    )

    df["EMA50"] = (
        close.ewm(span=50).mean()
    )

    # RSI

    delta = close.diff()

    gain = delta.clip(lower=0)

    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()

    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss

    df["RSI"] = (
        100 - (100 / (1 + rs))
    )

    # TARGET

    df["Target"] = np.where(
        df["Close"].shift(-1) > df["Close"],
        1,
        0
    )

    df = df.dropna()

    return df


# =========================
# TRAIN MODEL
# =========================

def train_model(df):

    features = [

        "EMA20",
        "EMA50",
        "RSI"

    ]

    X = df[features]

    y = df["Target"]

    model = RandomForestClassifier(
        n_estimators=100
    )

    model.fit(X, y)

    return model


# =========================
# MAIN SIGNAL
# =========================

@app.get("/signal")
def signal(balance: float = 100):

    df = get_data()

    df = add_features(df)

    model = train_model(df)

    latest = df.iloc[-1]

    features = [[

        latest["EMA20"],
        latest["EMA50"],
        latest["RSI"]

    ]]

    prediction = model.predict(features)[0]

    probability = max(
        model.predict_proba(features)[0]
    )

    current_price = round(
        float(latest["Close"]),
        1
    )

    support = round(
        float(df["Low"].tail(20).min()),
        1
    )

    resistance = round(
        float(df["High"].tail(20).max()),
        1
    )

    # FINAL SIGNAL

    if prediction == 1:

        final_signal = "BUY"

        sl = support

        tp = round(
            current_price +
            ((current_price - sl) * 2),
            1
        )

    else:

        final_signal = "SELL"

        sl = resistance

        tp = round(
            current_price -
            ((sl - current_price) * 2),
            1
        )

    # CONFIDENCE

    confidence = round(
        probability * 100,
        1
    )

    if confidence < 50:

        final_signal = "WAIT"

    # LOT SIZE

    risk_amount = balance * 0.02

    sl_distance = abs(
        current_price - sl
    )

    if sl_distance == 0:

        sl_distance = 1

    lot = round(
        risk_amount /
        (sl_distance * 10),
        2
    )

    if lot < 0.01:

        lot = 0.01

    # PROFIT / LOSS

    profit = round(
        abs(tp - current_price)
        * lot * 10,
        2
    )

    loss = round(
        abs(sl - current_price)
        * lot * 10,
        2
    )

    # MEMORY

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
# UPDATE RESULT
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
