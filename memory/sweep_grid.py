import asyncio, os, sys, itertools, json
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient
from market import MarketData
from engine import DEFAULT_CONFIG, merge
from backtest import Backtester, simulate_grid, summarize


async def main():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    bt = Backtester(MarketData(), db)
    st = await db.bot_state.find_one({"_id": "state"})
    cfg = merge(DEFAULT_CONFIG, st["config"])
    syms = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]
    hist = dict(zip(syms, await asyncio.gather(*[bt.fetch_history(s, 30) for s in syms])))
    res = []
    grid = dict(spacing=[0.25, 0.5, 0.8], levels=[3, 4, 6], trend=[False, True], adx=[0, 25, 35], atrm=[0, 1.5, 3.0], tf=["15m", "1h"])
    keys = list(grid)
    for combo in itertools.product(*[grid[k] for k in keys]):
        o = dict(zip(keys, combo))
        if not o["trend"] and not o["adx"] and o["tf"] == "1h":
            continue
        c = {**cfg, "filters": {**cfg["filters"], "htf_timeframe": o["tf"]},
             "grid": {**cfg["grid"], "spacing_pct": o["spacing"], "levels": o["levels"], "trend_filter": o["trend"], "adx_pause": o["adx"], "atr_spacing_mult": o["atrm"]}}
        per = {}
        allt = []
        for s, k in hist.items():
            tr = simulate_grid(s, k, c)
            per[s] = round(sum(x["pnl"] for x in tr), 1)
            allt += tr
        allt.sort(key=lambda t: t["closed_at"])
        sm = summarize(allt, 10000.0)
        res.append({**o, "trades": sm["trades"], "pnl": sm["pnl"], "wr": sm["win_rate"], "pf": sm["profit_factor"], "dd": sm["max_drawdown_pct"], "per": per})
        print(len(res), flush=True) if len(res) % 40 == 0 else None
    res.sort(key=lambda x: -x["pnl"])
    json.dump(res, open("/app/memory/sweep_grid.json", "w"), indent=1)
    print("positive:", sum(1 for x in res if x["pnl"] > 0), "/", len(res))
    for x in res[:25]:
        print(x)
    print("--- best per pf (>=100 trades)")
    for x in sorted([r for r in res if r["trades"] >= 100], key=lambda x: -x["pf"])[:8]:
        print(x)

asyncio.run(main())
