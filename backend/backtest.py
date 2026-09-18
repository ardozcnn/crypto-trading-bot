import asyncio
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import indicators
import strategies

BASELINE_OVERRIDES = {
    "min_score": 2.0, "atr_tp_sl": False, "partial_tp": False, "blacklist_losses": 0,
    "filters": {"htf_trend": False, "adx_min": 0, "volume_min_ratio": 0},
}


def variant(cfg: dict, overrides: dict) -> dict:
    out = {**cfg, **{k: v for k, v in overrides.items() if k != "filters"}}
    out["filters"] = {**cfg["filters"], **overrides.get("filters", {})}
    return out


class Backtester:
    def __init__(self, market, db):
        self.market = market
        self.db = db
        self.cache: dict[str, tuple[float, list[dict]]] = {}
        self.state = {"status": "idle", "progress": {}, "result": None, "error": None}
        self._task = None

    async def load_last(self):
        doc = await self.db.backtests.find_one({}, {"_id": 0}, sort=[("finished_at", -1)])
        if doc:
            self.state["result"] = doc
            self.state["status"] = "done"

    def start(self, cfg: dict, days: int):
        if self._task and not self._task.done():
            return False
        self.state = {"status": "running", "progress": {s: 0 for s in cfg["symbols"]}, "result": None, "error": None}
        self._task = asyncio.create_task(self._run(cfg, days))
        return True

    async def _run(self, cfg: dict, days: int):
        t0 = time.time()
        try:
            hist = dict(zip(cfg["symbols"], await asyncio.gather(*[self.fetch_history(s, days) for s in cfg["symbols"]])))
            variants = {"baseline": variant(cfg, BASELINE_OVERRIDES), "current": cfg}
            result = {"days": days, "symbols": cfg["symbols"], "candles": sum(len(v) for v in hist.values()),
                      "from": min(v[0]["t"] for v in hist.values() if v), "to": max(v[-1]["t"] for v in hist.values() if v),
                      "variants": {}, "finished_at": datetime.now(timezone.utc).isoformat()}
            for name, vcfg in variants.items():
                trades = []
                for s, k in hist.items():
                    if len(k) > 200:
                        trades += await asyncio.to_thread(simulate_symbol, s, k, vcfg)
                trades.sort(key=lambda t: t["closed_at"])
                result["variants"][name] = summarize(trades, float(cfg["initial_balance"]))
            gtrades = []
            for s in cfg["grid"]["symbols"]:
                k = hist.get(s) or await self.fetch_history(s, days)
                if len(k) > 200:
                    gtrades += await asyncio.to_thread(simulate_grid, s, k, cfg)
            gtrades.sort(key=lambda t: t["closed_at"])
            result["variants"]["grid"] = summarize(gtrades, float(cfg["initial_balance"]))
            result["grid_symbols"] = cfg["grid"]["symbols"]
            result["duration_sec"] = round(time.time() - t0, 1)
            await self.db.backtests.insert_one(dict(result))
            self.state.update(status="done", result=result)
        except Exception as e:
            self.state.update(status="error", error=str(e))

    async def fetch_history(self, symbol: str, days: int) -> list[dict]:
        cached = self.cache.get(symbol)
        if cached and time.time() - cached[0] < 1800 and len(cached[1]) >= days * 1440 * 0.95:
            self.state["progress"][symbol] = 100
            return cached[1][-days * 1440:]
        end = int(time.time() * 1000)
        start = end - days * 86400_000
        out, cur = [], start
        while cur < end:
            r = await self.market.client.get("/fapi/v1/klines", params={"symbol": symbol, "interval": "1m", "startTime": cur, "limit": 1500})
            r.raise_for_status()
            rows = r.json()
            if not rows:
                break
            out += [{"t": k[0], "o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5])} for k in rows]
            cur = rows[-1][0] + 60_000
            self.state["progress"][symbol] = min(99, int((cur - start) / (end - start) * 100))
            await asyncio.sleep(0.05)
        self.state["progress"][symbol] = 100
        self.cache[symbol] = (time.time(), out)
        return out


def precompute(klines: list[dict], cfg: dict) -> pd.DataFrame:
    p = cfg["indicators"]
    df = pd.DataFrame(klines)
    c = df["c"]
    df["ema_fast"], df["ema_slow"] = indicators.ema(c, p["ema_fast"]), indicators.ema(c, p["ema_slow"])
    df["rsi"] = indicators.rsi(c, p["rsi_period"])
    _, _, df["macd_hist"] = indicators.macd(c, p["macd_fast"], p["macd_slow"], p["macd_signal"])
    mid, up, lo = indicators.bollinger(c, p["bb_period"], p["bb_std"])
    width = up - lo
    df["pct_b"] = ((c - lo) / width.replace(0, np.nan)).fillna(0.5)
    df["atr"] = indicators.atr(df, 14)
    df["adx"] = indicators.adx(df, 14)
    prev_vol = df["v"].shift(1)
    df["vol_ratio"] = (prev_vol / prev_vol.rolling(20).mean()).fillna(1.0)
    f = cfg["filters"]
    ts = pd.to_datetime(df["t"], unit="ms")
    tf = {"5m": "5min", "15m": "15min", "1h": "1h"}.get(f.get("htf_timeframe", "15m"), "15min")
    htf_close = c.groupby(ts.dt.floor(tf)).last()
    htf_ema = indicators.ema(htf_close, f.get("htf_ema", 50))
    slope = (htf_ema - htf_ema.shift(3)) / htf_ema.shift(3) * 100
    trend = pd.Series(np.where((htf_close > htf_ema) & (slope > -0.02), "UP", np.where((htf_close < htf_ema) & (slope < 0.02), "DOWN", "FLAT")), index=htf_close.index)
    trend = trend.shift(1)  # only completed HTF bars
    df["htf_trend"] = trend.reindex(ts.dt.floor(tf)).ffill().values
    return df


def simulate_symbol(symbol: str, klines: list[dict], cfg: dict) -> list[dict]:
    df = precompute(klines, cfg)
    p, f = cfg["indicators"], cfg["filters"]
    lev, fee = cfg["leverage"], cfg["fee_pct"] / 100
    margin_full = float(cfg["initial_balance"]) * cfg["risk_per_trade_pct"] / 100
    cols = {k: df[k].to_numpy() for k in ("t", "o", "h", "l", "c", "rsi", "macd_hist", "pct_b", "ema_fast", "ema_slow", "atr", "adx", "vol_ratio")}
    htf = df["htf_trend"].tolist()
    trades, pos = [], None
    cooldown_until, blacklist_until, streak = 0, 0, 0
    warm = max(60, p["bb_period"] + 5)

    for i in range(warm, len(df)):
        t, o, h, l, c = cols["t"][i], cols["o"][i], cols["h"][i], cols["l"][i], cols["c"][i]
        ind = {
            "close": c, "rsi": cols["rsi"][i], "rsi_prev": cols["rsi"][i - 1],
            "macd_hist": cols["macd_hist"][i], "macd_hist_prev": cols["macd_hist"][i - 1], "pct_b": cols["pct_b"][i],
            "ema_fast": cols["ema_fast"][i], "ema_slow": cols["ema_slow"][i], "ema_fast_prev": cols["ema_fast"][i - 1], "ema_slow_prev": cols["ema_slow"][i - 1],
            "adx": cols["adx"][i], "vol_ratio": cols["vol_ratio"][i], "atr": cols["atr"][i],
        }
        sig = strategies.multi_signal(ind, p, cfg["min_score"], f, {"trend": htf[i]} if isinstance(htf[i], str) else None)

        if pos:
            long = pos["side"] == "LONG"
            d = 1 if long else -1
            exit_price, reason = None, None
            hit_sl = l <= pos["sl"] if long else h >= pos["sl"]
            hit_tp = h >= pos["tp"] if long else l <= pos["tp"]
            if cfg["partial_tp"] and not pos["partial"] and not hit_sl:
                half = pos["entry"] + (pos["tp"] - pos["entry"]) * 0.5
                if (long and h >= half) or (not long and l <= half):
                    frac = cfg["partial_tp_fraction"]
                    q = pos["qty"] * frac
                    net = (half - pos["entry"]) * q * d - half * q * fee - pos["entry"] * q * fee
                    trades.append(_trade(symbol, pos, half, net, pos["margin"] * frac, t, "KISMİ TP"))
                    pos["qty"] -= q
                    pos["margin"] *= 1 - frac
                    pos["partial"] = True
                    pos["sl"] = pos["entry"]
                    hit_sl = l <= pos["sl"] if long else h >= pos["sl"]
            if hit_sl:
                exit_price, reason = pos["sl"], "STOP LOSS"
            elif hit_tp:
                exit_price, reason = pos["tp"], "TAKE PROFIT"
            else:
                pos["peak"] = max(pos["peak"], h) if long else min(pos["peak"], l)
                fav = (pos["peak"] - pos["entry"]) / pos["entry"] * 100 * d
                if cfg["trailing"] and fav >= cfg["trailing_activation_pct"]:
                    new_sl = pos["peak"] * (1 - cfg["trailing_distance_pct"] / 100 * d)
                    if pos["tsl"] is None or (long and new_sl > pos["tsl"]) or (not long and new_sl < pos["tsl"]):
                        pos["tsl"] = new_sl
                if pos["tsl"] is not None and ((long and l <= pos["tsl"]) or (not long and h >= pos["tsl"])):
                    exit_price, reason = pos["tsl"], "TRAILING STOP"
                elif (t - pos["t"]) / 60_000 >= cfg["max_hold_minutes"]:
                    exit_price, reason = c, "SÜRE DOLDU"
                elif sig["side"] and sig["side"] != pos["side"] and (c - pos["entry"]) * d > 0:
                    exit_price, reason = c, "TERS SİNYAL"
            if exit_price is not None:
                q = pos["qty"]
                net = (exit_price - pos["entry"]) * q * d - exit_price * q * fee - pos["entry"] * q * fee
                trades.append(_trade(symbol, pos, exit_price, net, pos["margin"], t, reason))
                cooldown_until = t + cfg["cooldown_seconds"] * 1000
                total = net + sum(x["pnl"] for x in trades if x.get("pos_id") == pos["id"] and x["exit_reason"] == "KISMİ TP")
                streak = 0 if total >= 0 else streak + 1
                if cfg["blacklist_losses"] and streak >= cfg["blacklist_losses"]:
                    blacklist_until = t + cfg["blacklist_minutes"] * 60_000
                    streak = 0
                pos = None
            continue

        if not sig["side"] or t < cooldown_until or t < blacklist_until:
            continue
        d = 1 if sig["side"] == "LONG" else -1
        tp_dist, sl_dist = c * cfg["tp_pct"] / 100, c * cfg["sl_pct"] / 100
        if cfg["atr_tp_sl"] and ind["atr"] > 0:
            tp_dist = min(max(ind["atr"] * cfg["atr_tp_mult"], c * 0.002), c * 0.015)
            sl_dist = min(max(ind["atr"] * cfg["atr_sl_mult"], c * 0.0015), c * 0.01)
            tp_dist = max(tp_dist, sl_dist * 1.2)
        pos = {"id": f"{symbol}-{t}", "side": sig["side"], "entry": c, "qty": margin_full * lev / c, "margin": margin_full,
               "tp": c + tp_dist * d, "sl": c - sl_dist * d, "tsl": None, "peak": c, "t": t, "partial": False}
    return trades


def htf_series(klines: list[dict], cfg: dict) -> tuple[list, list]:
    """Per-1m-candle HTF trend label and HTF ADX (only completed HTF bars)."""
    f = cfg["filters"]
    df = pd.DataFrame(klines)
    ts = pd.to_datetime(df["t"], unit="ms")
    tf = {"5m": "5min", "15m": "15min", "1h": "1h"}.get(f.get("htf_timeframe", "15m"), "15min")
    key = ts.dt.floor(tf)
    g = df.groupby(key)
    h = pd.DataFrame({"o": g["o"].first(), "h": g["h"].max(), "l": g["l"].min(), "c": g["c"].last()})
    e = indicators.ema(h["c"], f.get("htf_ema", 50))
    slope = (e - e.shift(3)) / e.shift(3) * 100
    trend = pd.Series(np.where((h["c"] > e) & (slope > -0.02), "UP", np.where((h["c"] < e) & (slope < 0.02), "DOWN", "FLAT")), index=h.index).shift(1)
    hadx = indicators.adx(h, 14).shift(1)
    return trend.reindex(key).ffill().tolist(), hadx.reindex(key).ffill().fillna(0).tolist()


def simulate_grid(symbol: str, klines: list[dict], cfg: dict) -> list[dict]:
    g, lev, fee = cfg["grid"], cfg["leverage"], cfg["fee_pct"] / 100
    margin = float(cfg["initial_balance"]) * g["size_pct"] / 100
    trend_filter, adx_pause = g.get("trend_filter", False), g.get("adx_pause", 0)
    trend, hadx = htf_series(klines, cfg) if (trend_filter or adx_pause) else ([None] * len(klines), [0] * len(klines))
    trades, open_pos = [], {}
    center, levels, step, band = None, None, 0.0, 0.0
    atr = indicators.atr(pd.DataFrame(klines), 14).tolist() if g.get("atr_spacing_mult") else None
    prev_c = klines[0]["c"]
    for i in range(1, len(klines)):
        k = klines[i]
        t, h, l, c = k["t"], k["h"], k["l"], k["c"]
        if center is None or (not open_pos and abs(c - center) / center > band):
            center = c
            spacing = g["spacing_pct"]
            if atr and atr[i] and not np.isnan(atr[i]):
                spacing = max(g["spacing_pct"], atr[i] / c * 100 * g["atr_spacing_mult"])
            step = spacing / 100
            band = (g["levels"] + 2) * spacing / 100
            levels = strategies.grid_levels(center, g["levels"], spacing)
            prev_c = c
            continue
        for key, pos in list(open_pos.items()):
            long = pos["side"] == "LONG"
            d = 1 if long else -1
            hit_sl = l <= pos["sl"] if long else h >= pos["sl"]
            hit_tp = h >= pos["tp"] if long else l <= pos["tp"]
            if hit_sl or hit_tp:
                px, reason = (pos["sl"], "STOP LOSS") if hit_sl else (pos["tp"], "TAKE PROFIT")
                net = (px - pos["entry"]) * pos["qty"] * d - px * pos["qty"] * fee - pos["entry"] * pos["qty"] * fee
                trades.append(_trade(symbol, pos, px, net, margin, t, reason))
                del open_pos[key]
        paused = adx_pause and hadx[i] > adx_pause
        allow_long = not paused and (not trend_filter or trend[i] != "DOWN")
        allow_short = not paused and (not trend_filter or trend[i] != "UP")
        if allow_long:
            for j, lvl in enumerate(levels["buy"]):
                key = f"B{j}"
                if key not in open_pos and prev_c > lvl >= l:
                    open_pos[key] = {"id": f"{symbol}-{key}-{t}", "side": "LONG", "entry": lvl, "qty": margin * lev / lvl, "tp": lvl * (1 + step), "sl": center * (1 - band), "t": t}
        if allow_short:
            for j, lvl in enumerate(levels["sell"]):
                key = f"S{j}"
                if key not in open_pos and prev_c < lvl <= h:
                    open_pos[key] = {"id": f"{symbol}-{key}-{t}", "side": "SHORT", "entry": lvl, "qty": margin * lev / lvl, "tp": lvl * (1 - step), "sl": center * (1 + band), "t": t}
        prev_c = c
    return trades


def _trade(symbol, pos, price, net, margin, t, reason) -> dict:
    return {
        "pos_id": pos["id"], "symbol": symbol, "side": pos["side"], "entry_price": float(pos["entry"]), "exit_price": round(float(price), 6),
        "pnl": round(float(net), 4), "pnl_pct": round(float(net) / float(margin) * 100, 2), "opened_at": int(pos["t"]), "closed_at": int(t),
        "exit_reason": reason, "duration_min": int((t - pos["t"]) / 60_000),
    }


def summarize(trades: list[dict], initial: float) -> dict:
    wins = [x for x in trades if x["pnl"] > 0]
    gw = sum(x["pnl"] for x in wins)
    gl = abs(sum(x["pnl"] for x in trades if x["pnl"] <= 0))
    eq, peak, max_dd = initial, initial, 0.0
    daily: dict[str, dict] = {}
    for x in trades:
        eq += x["pnl"]
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak * 100)
        day = datetime.fromtimestamp(x["closed_at"] / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        dd = daily.setdefault(day, {"date": day, "trades": 0, "wins": 0, "pnl": 0.0})
        dd["trades"] += 1
        dd["wins"] += int(x["pnl"] > 0)
        dd["pnl"] = round(dd["pnl"] + x["pnl"], 2)
    by_symbol: dict[str, dict] = {}
    for x in trades:
        s = by_symbol.setdefault(x["symbol"], {"symbol": x["symbol"], "trades": 0, "wins": 0, "pnl": 0.0})
        s["trades"] += 1
        s["wins"] += int(x["pnl"] > 0)
        s["pnl"] = round(s["pnl"] + x["pnl"], 2)
    reasons: dict[str, dict] = {}
    for x in trades:
        r = reasons.setdefault(x["exit_reason"], {"reason": x["exit_reason"], "trades": 0, "pnl": 0.0})
        r["trades"] += 1
        r["pnl"] = round(r["pnl"] + x["pnl"], 2)
    total = round(sum(x["pnl"] for x in trades), 2)
    return {
        "trades": len(trades), "wins": len(wins), "losses": len(trades) - len(wins),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "pnl": total, "roi_pct": round(total / initial * 100, 2),
        "profit_factor": round(gw / gl, 2) if gl else (round(gw, 2) if gw else 0.0),
        "avg_pnl": round(total / len(trades), 2) if trades else 0.0,
        "max_drawdown_pct": round(max_dd, 2),
        "best": round(max((x["pnl"] for x in trades), default=0.0), 2),
        "worst": round(min((x["pnl"] for x in trades), default=0.0), 2),
        "daily": sorted(daily.values(), key=lambda d: d["date"]),
        "by_symbol": sorted(by_symbol.values(), key=lambda s: -s["pnl"]),
        "exit_reasons": sorted(reasons.values(), key=lambda r: -r["trades"]),
        "equity_curve": _curve(trades, initial),
    }


def _curve(trades: list[dict], initial: float) -> list[dict]:
    pts, eq = [], initial
    step = max(1, len(trades) // 200)
    for i, x in enumerate(trades):
        eq += x["pnl"]
        if i % step == 0 or i == len(trades) - 1:
            pts.append({"t": x["closed_at"], "equity": round(eq, 2)})
    return pts

