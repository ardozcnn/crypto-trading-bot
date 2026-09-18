import asyncio, os, sys, time
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from market import MarketData
from engine import DEFAULT_CONFIG, merge
from backtest import Backtester, simulate_symbol, summarize


def resample(klines, minutes):
    df = pd.DataFrame(klines)
    df["ts"] = pd.to_datetime(df["t"], unit="ms")
    g = df.groupby(df["ts"].dt.floor(f"{minutes}min"))
    out = pd.DataFrame({"t": g["t"].first(), "o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last(), "v": g["v"].sum()})
    return out.to_dict(orient="records")


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    bt = Backtester(MarketData(), db)
    st = await db.bot_state.find_one({"_id": "state"})
    cfg = merge(DEFAULT_CONFIG, st["config"])
    hist = dict(zip(cfg["symbols"], await asyncio.gather(*[bt.fetch_history(s, 30) for s in cfg["symbols"]])))
    tests = []
    for tf in (5, 15):
        h = {s: resample(k, tf) for s, k in hist.items()}
        for score in (2.0, 2.5):
            for trend in (True, False):
                for adx in (0, 20):
                    for tpm, slm in ((2.0, 1.0), (3.0, 1.5), (4.0, 2.0)):
                        for hold in (240, 720):
                            for partial in (True, False):
                                c = {**cfg, "min_score": score, "atr_tp_sl": True, "atr_tp_mult": tpm, "atr_sl_mult": slm, "max_hold_minutes": hold,
                                     "partial_tp": partial, "trailing_activation_pct": 0.6, "trailing_distance_pct": 0.3,
                                     "filters": {**cfg["filters"], "htf_timeframe": "1h" if tf == 15 else "15m", "adx_min": adx, "volume_min_ratio": 0, "htf_trend": trend}}
                                trades = []
                                for s, k in h.items():
                                    trades += simulate_symbol(s, k, c)
                                trades.sort(key=lambda t: t["closed_at"])
                                sm = summarize(trades, 10000.0)
                                tests.append({"tf": tf, "score": score, "trend": trend, "adx": adx, "tp": tpm, "sl": slm, "hold": hold, "partial": partial,
                                              "trades": sm["trades"], "pnl": sm["pnl"], "wr": sm["win_rate"], "pf": sm["profit_factor"], "dd": sm["max_drawdown_pct"]})
    tests.sort(key=lambda x: -x["pnl"])
    print("positive:", sum(1 for x in tests if x["pnl"] > 0), "/", len(tests))
    for x in tests[:20]:
        print(x)
    print("--- worst 3")
    for x in tests[-3:]:
        print(x)

asyncio.run(main())
