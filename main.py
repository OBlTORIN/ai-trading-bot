from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import random

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

    current_price = round(random.uniform(4680, 4720), 1)

    ema20 = random.uniform(4685, 4715)
    ema50 = random.uniform(4685, 4715)

    rsi = random.randint(30, 80)

    volume_strength = random.randint(50, 100)

    support = round(current_price - random.uniform(5, 15), 1)
    resistance = round(current_price + random.uniform(5, 15), 1)

    # TREND DETECTION

    if ema20 > ema50:
        trend = "BUY"
    else:
        trend = "SELL"

    # RSI FILTER

    if rsi > 70:
        signal = "SELL"

    elif rsi < 35:
        signal = "BUY"

    else:
        signal = trend

    # ENTRY / SL / TP

    entry = current_price

    if signal == "BUY":

        sl = round(entry - 10, 1)

        tp = round(entry + 20, 1)

    else:

        sl = round(entry + 10, 1)

        tp = round(entry - 20, 1)

    # LOT SIZE

    risk_amount = balance * 0.02

    sl_distance = abs(entry - sl)

    lot = round(risk_amount / (sl_distance * 10), 2)

    if lot < 0.01:
        lot = 0.01

    # PROFIT / LOSS

    profit = round(abs(tp - entry) * lot * 10, 2)

    loss = round(abs(sl - entry) * lot * 10, 2)

    # CONFIDENCE

    confidence = 60

    if trend == signal:
        confidence += 10

    if volume_strength > 70:
        confidence += 10

    if rsi < 35 or rsi > 70:
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

        "confidence": f"{confidence}%",

        "ema20": round(ema20, 1),

        "ema50": round(ema50, 1),

        "rsi": rsi,

        "volume": volume_strength,

        "support": support,

        "resistance": resistance

    }


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
