import asyncio, itertools, json, os, sys, time
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient
from market import MarketData
from engine import DEFAULT_CONFIG, merge
from backtest import Backtester, simulate_symbol, summarize

async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    bt = Backtester(MarketData(), db)
    st = await db.bot_state.find_one({"_id": "state"})
    cfg = merge(DEFAULT_CONFIG, st["config"])
    hist = dict(zip(cfg["symbols"], await asyncio.gather(*[bt.fetch_history(s, 30) for s in cfg["symbols"]])))
    print("fetched", {k: len(v) for k, v in hist.items()}, flush=True)
    grid = {
        "timeframe_note": ["1m"],
        "min_score": [2.0, 2.5, 3.0],
        "adx_min": [0, 15, 20, 25],
        "volume_min_ratio": [0, 0.8],
        "htf_trend": [True, False],
        "atr_tp_mult": [1.5, 2.5, 3.5],
        "atr_sl_mult": [1.0, 1.5],
        "max_hold_minutes": [45, 120],
        "partial_tp": [True, False],
    }
    keys = [k for k in grid if k != "timeframe_note"]
    results = []
    t0 = time.time()
    for combo in itertools.product(*[grid[k] for k in keys]):
        o = dict(zip(keys, combo))
        c = {**cfg, "min_score": o["min_score"], "atr_tp_mult": o["atr_tp_mult"], "atr_sl_mult": o["atr_sl_mult"],
             "max_hold_minutes": o["max_hold_minutes"], "partial_tp": o["partial_tp"], "atr_tp_sl": True,
             "filters": {**cfg["filters"], "adx_min": o["adx_min"], "volume_min_ratio": o["volume_min_ratio"], "htf_trend": o["htf_trend"]}}
        trades = []
        for s, k in hist.items():
            trades += simulate_symbol(s, k, c)
        trades.sort(key=lambda t: t["closed_at"])
        sm = summarize(trades, 10000.0)
        results.append({**o, "trades": sm["trades"], "pnl": sm["pnl"], "win_rate": sm["win_rate"], "pf": sm["profit_factor"], "dd": sm["max_drawdown_pct"]})
        if len(results) % 50 == 0:
            print(len(results), "done", round(time.time() - t0), "s", flush=True)
    results.sort(key=lambda r: -r["pnl"])
    json.dump(results, open("/app/memory/sweep_results.json", "w"), indent=1)
    print("TOP 15")
    for r in results[:15]:
        print(r)
    print("current-like:")
    for r in results:
        if r["min_score"] == 2.5 and r["adx_min"] == 20 and r["volume_min_ratio"] == 0.8 and r["htf_trend"] and r["atr_tp_mult"] == 1.5 and r["atr_sl_mult"] == 1.0 and r["max_hold_minutes"] == 45 and r["partial_tp"]:
            print(r)

asyncio.run(main())
