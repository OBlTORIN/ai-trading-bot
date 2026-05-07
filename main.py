from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import yfinance as yf
import pandas as pd
import numpy as np

import tensorflow as tf

from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

import MetaTrader5 as mt5

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
# MT5 LOGIN
# =========================

MT5_LOGIN = 12345678
MT5_PASSWORD = "YOUR_PASSWORD"
MT5_SERVER = "YOUR_BROKER_SERVER"

mt5.initialize()

mt5.login(
    MT5_LOGIN,
    password=MT5_PASSWORD,
    server=MT5_SERVER
)


# =========================
# MEMORY
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
# GET DATA
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
# FEATURES
# =========================

def add_features(df):

    close = df["Close"]

    high = df["High"]

    low = df["Low"]

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

    # ATR

    high_low = high - low

    high_close = np.abs(
        high - close.shift()
    )

    low_close = np.abs(
        low - close.shift()
    )

    ranges = pd.concat([

        high_low,
        high_close,
        low_close

    ], axis=1)

    true_range = np.max(
        ranges,
        axis=1
    )

    df["ATR"] = (
        true_range.rolling(14).mean()
    )

    # TARGET

    df["Target"] = np.where(

        df["Close"].shift(-1)
        > df["Close"],

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
        "RSI",
        "ATR"

    ]

    X = df[features].values

    y = df["Target"].values

    model = Sequential()

    model.add(
        Dense(
            32,
            activation="relu",
            input_shape=(4,)
        )
    )

    model.add(
        Dense(
            16,
            activation="relu"
        )
    )

    model.add(
        Dense(
            1,
            activation="sigmoid"
        )
    )

    model.compile(

        optimizer="adam",

        loss="binary_crossentropy",

        metrics=["accuracy"]

    )

    model.fit(

        X,
        y,

        epochs=10,

        batch_size=32,

        verbose=0

    )

    return model


# =========================
# EXECUTE TRADE
# =========================

def execute_trade(signal, lot, sl, tp):

    symbol = "XAUUSD"

    symbol_info = mt5.symbol_info(symbol)

    if symbol_info is None:

        return "Symbol Not Found"

    tick = mt5.symbol_info_tick(symbol)

    if signal == "BUY":

        order_type = mt5.ORDER_TYPE_BUY

        price = tick.ask

    else:

        order_type = mt5.ORDER_TYPE_SELL

        price = tick.bid

    request = {

        "action": mt5.TRADE_ACTION_DEAL,

        "symbol": symbol,

        "volume": lot,

        "type": order_type,

        "price": price,

        "sl": sl,

        "tp": tp,

        "deviation": 20,

        "magic": 123456,

        "comment": "AI BOT",

        "type_time": mt5.ORDER_TIME_GTC,

        "type_filling": mt5.ORDER_FILLING_IOC,

    }

    result = mt5.order_send(request)

    return str(result)


# =========================
# MAIN SIGNAL
# =========================

@app.get("/signal")
def signal(balance: float = 100):

    df = get_data()

    df = add_features(df)

    model = train_model(df)

    latest = df.iloc[-1]

    atr = round(
        float(latest["ATR"]),
        1
    )

    features = np.array([[

        latest["EMA20"],
        latest["EMA50"],
        latest["RSI"],
        latest["ATR"]

    ]])

    prediction = model.predict(
        features,
        verbose=0
    )[0][0]

    current_price = round(
        float(latest["Close"]),
        1
    )

    # SIGNAL

    if prediction > 0.55:

        final_signal = "BUY"

        sl = round(
            current_price - (atr * 1.5),
            1
        )

        tp = round(
            current_price + (atr * 3),
            1
        )

    elif prediction < 0.45:

        final_signal = "SELL"

        sl = round(
            current_price + (atr * 1.5),
            1
        )

        tp = round(
            current_price - (atr * 3),
            1
        )

    else:

        final_signal = "WAIT"

        sl = current_price

        tp = current_price

    # CONFIDENCE

    confidence = round(

        abs(prediction - 0.5)
        * 200,

        1

    )

    if confidence < 50:
        confidence = 50

    # LOT SIZE

    risk_amount = balance * 0.01

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

    # AUTO EXECUTION

    trade_result = "No Trade"

    if final_signal != "WAIT":

        trade_result = execute_trade(

            final_signal,
            lot,
            sl,
            tp

        )

    # PROFIT LOSS

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

    return {

        "signal": final_signal,

        "entry": current_price,

        "sl": sl,

        "tp": tp,

        "lot": lot,

        "profit": profit,

        "loss": loss,

        "confidence": f"{confidence}%",

        "execution": trade_result

    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
