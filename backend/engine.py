import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta

from market import MarketData
import indicators
import strategies

logger = logging.getLogger("engine")

DEFAULT_CONFIG = {
    "strategy": "both",
    "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"],
    "timeframe": "1m",
    "leverage": 10,
    "risk_per_trade_pct": 5.0,
    "max_open_positions": 8,
    "tp_pct": 0.6,
    "sl_pct": 0.35,
    "trailing": True,
    "trailing_activation_pct": 0.3,
    "trailing_distance_pct": 0.15,
    "max_hold_minutes": 45,
    "cooldown_seconds": 45,
    "min_score": 2.5,
    "filters": {"htf_trend": True, "htf_timeframe": "15m", "htf_ema": 50, "adx_min": 20.0, "volume_min_ratio": 0.8},
    "atr_tp_sl": True,
    "atr_tp_mult": 1.5,
    "atr_sl_mult": 1.0,
    "partial_tp": True,
    "partial_tp_fraction": 0.5,
    "daily_loss_limit_pct": 3.0,
    "blacklist_losses": 3,
    "blacklist_minutes": 120,
    "indicators": {
        "rsi_period": 14, "rsi_buy": 35, "rsi_sell": 65,
        "ema_fast": 9, "ema_slow": 21,
        "bb_period": 20, "bb_std": 2.0,
        "macd_fast": 12, "macd_slow": 26, "macd_signal": 9,
    },
    "grid": {"levels": 6, "spacing_pct": 0.25, "size_pct": 2.5, "symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]},
    "initial_balance": 10000.0,
    "fee_pct": 0.04,
}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in (override or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


class BotEngine:
    def __init__(self, db):
        self.db = db
        self.market = MarketData()
        self.config = dict(DEFAULT_CONFIG)
        self.running = False
        self.balance = DEFAULT_CONFIG["initial_balance"]
        self.positions: dict[str, dict] = {}
        self.trades: list[dict] = []
        self.logs: list[dict] = []
        self.equity: list[dict] = []
        self.signals: dict[str, dict] = {}
        self.grids: dict[str, dict] = {}
        self.cooldowns: dict[str, datetime] = {}
        self.last_prices: dict[str, float] = {}
        self.htf: dict[str, dict] = {}
        self.loss_streak: dict[str, int] = {}
        self.blacklist: dict[str, str] = {}
        self.day: dict = {"date": None, "start_equity": None, "halted": False}
        self.first_started_at: str | None = None
        self.total_active_sec = 0.0
        self.session_started_at = now_iso()
        self._last_tick_ts: datetime | None = None
        self._tick = 0
        self._last_equity_ts = None
        self._task = None
        self.loop_interval = 4

    # ---------- persistence ----------
    async def load(self):
        st = await self.db.bot_state.find_one({"_id": "state"})
        if st:
            self.config = merge(DEFAULT_CONFIG, st.get("config", {}))
            self.balance = st.get("balance", self.balance)
            self.running = st.get("running", False)
            self.grids = st.get("grids", {})
            self.blacklist = st.get("blacklist", {})
            self.loss_streak = st.get("loss_streak", {})
            self.day = st.get("day", self.day)
            self.first_started_at = st.get("first_started_at")
            self.total_active_sec = st.get("total_active_sec", 0.0)
        self.positions = {p["id"]: p async for p in self.db.positions.find({}, {"_id": 0})}
        self.trades = await self.db.trades.find({}, {"_id": 0}).sort("closed_at", -1).to_list(2000)
        self.logs = await self.db.logs.find({}, {"_id": 0}).sort("ts", -1).to_list(300)
        eq = await self.db.equity.find({}, {"_id": 0}).sort("t", -1).to_list(1500)
        self.equity = list(reversed(eq))
        if st and "total_active_sec" not in st:
            await self._backfill_uptime()

    async def _backfill_uptime(self):
        ts = [datetime.fromisoformat(e["t"]) async for e in self.db.equity.find({}, {"t": 1}).sort("t", 1)]
        if ts:
            self.first_started_at = ts[0].isoformat()
            self.total_active_sec = sum(g for g in ((b - a).total_seconds() for a, b in zip(ts, ts[1:])) if g < 600)
        await self.save_state()

    async def save_state(self):
        await self.db.bot_state.update_one(
            {"_id": "state"},
            {"$set": {
                "config": self.config, "balance": self.balance, "running": self.running, "grids": self.grids,
                "blacklist": self.blacklist, "loss_streak": self.loss_streak, "day": self.day,
                "first_started_at": self.first_started_at, "total_active_sec": self.total_active_sec,
            }},
            upsert=True,
        )

    async def log(self, level: str, msg: str, symbol: str | None = None, data: dict | None = None):
        entry = {"id": str(uuid.uuid4()), "ts": now_iso(), "level": level, "msg": msg, "symbol": symbol, "data": data or {}}
        self.logs.insert(0, entry)
        self.logs = self.logs[:300]
        await self.db.logs.insert_one(dict(entry))
        logger.info("[%s] %s %s", level, symbol or "", msg)

    # ---------- lifecycle ----------
    def start_loop(self):
        if not self._task:
            self._task = asyncio.create_task(self._loop())

    async def start(self):
        if self.running:
            return
        self.running = True
        if not self.first_started_at:
            self.first_started_at = now_iso()
        self.session_started_at = now_iso()
        self._last_tick_ts = None
        await self.save_state()
        await self.log("info", f"Bot başlatıldı · strateji={self.config['strategy']} · kaldıraç={self.config['leverage']}x")

    async def stop(self):
        self.running = False
        await self.save_state()
        await self.log("warn", "Bot durduruldu")

    async def reset(self):
        was_running = self.running
        self.running = False
        self.balance = float(self.config["initial_balance"])
        self.positions, self.trades, self.logs, self.equity, self.grids, self.cooldowns = {}, [], [], [], {}, {}
        self.blacklist, self.loss_streak = {}, {}
        self.day = {"date": None, "start_equity": None, "halted": False}
        for col in ("positions", "trades", "logs", "equity"):
            await self.db[col].delete_many({})
        await self.save_state()
        await self.log("info", f"Hesap sıfırlandı · başlangıç bakiyesi {self.balance:,.2f} USDT")
        if was_running:
            await self.start()

    async def update_config(self, patch: dict):
        old_symbols = set(self.config["grid"]["symbols"])
        self.config = merge(self.config, patch)
        if set(self.config["grid"]["symbols"]) != old_symbols:
            self.grids = {}
        await self.save_state()
        await self.log("info", "Ayarlar güncellendi")
        return self.config

    def all_symbols(self) -> set[str]:
        return set(self.config["symbols"]) | set(self.config["grid"]["symbols"])

    # ---------- main loop ----------
    async def _loop(self):
        while True:
            try:
                await self.tick()
            except Exception as e:
                logger.exception("tick error")
                await self.log("error", f"Döngü hatası: {e}")
            await asyncio.sleep(self.loop_interval)

    async def tick(self):
        self._tick += 1
        now = datetime.now(timezone.utc)
        symbols = self.all_symbols()
        prices = await self.market.fetch_prices(symbols)
        if self._tick % 15 == 1:
            await self.refresh_htf(symbols)
        if self._tick % 3 == 1:
            await self.refresh_signals(symbols)
        if self._tick % 8 == 1:
            await self.market.fetch_tickers(symbols)
        if self.running:
            if self._last_tick_ts:
                self.total_active_sec += min((now - self._last_tick_ts).total_seconds(), 60)
            self._last_tick_ts = now
            await self.roll_day(prices)
            await self.manage_positions(prices)
            if not self.day["halted"]:
                await self.evaluate_multi(prices)
                await self.evaluate_grid(prices)
            await self.snapshot_equity(prices)
        else:
            self._last_tick_ts = None
        self.last_prices = dict(prices)

    async def roll_day(self, prices: dict[str, float]):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.day.get("date") != today:
            self.day = {"date": today, "start_equity": round(self.compute_equity(prices), 2), "halted": False}
            await self.save_state()
            return
        limit = self.config["daily_loss_limit_pct"]
        if limit and not self.day["halted"] and self.day.get("start_equity"):
            dd = (self.compute_equity(prices) - self.day["start_equity"]) / self.day["start_equity"] * 100
            if dd <= -limit:
                self.day["halted"] = True
                await self.save_state()
                await self.log("error", f"GÜNLÜK ZARAR LİMİTİ ({limit:g}%) aşıldı · yeni işlem açılmayacak, gün sonunda (UTC) devam eder")

    def is_blacklisted(self, symbol: str) -> bool:
        until = self.blacklist.get(symbol)
        if not until:
            return False
        if datetime.fromisoformat(until) <= datetime.now(timezone.utc):
            self.blacklist.pop(symbol, None)
            self.loss_streak[symbol] = 0
            return False
        return True

    async def refresh_htf(self, symbols: set[str]):
        f = self.config["filters"]
        if not f.get("htf_trend"):
            return
        results = await asyncio.gather(
            *[self.market.fetch_klines(s, f["htf_timeframe"], max(f["htf_ema"] + 10, 60), store=False) for s in symbols], return_exceptions=True
        )
        for s, res in zip(symbols, results):
            if not isinstance(res, Exception) and len(res) >= f["htf_ema"] + 4:
                self.htf[s] = indicators.htf_trend(res, f["htf_ema"])

    async def refresh_signals(self, symbols: set[str]):
        results = await asyncio.gather(
            *[self.market.fetch_klines(s, self.config["timeframe"], 150) for s in symbols], return_exceptions=True
        )
        for s, res in zip(symbols, results):
            if isinstance(res, Exception) or len(res) < 40:
                continue
            ind = indicators.compute(res, self.config["indicators"])
            sig = strategies.multi_signal(ind, self.config["indicators"], self.config["min_score"], self.config["filters"], self.htf.get(s))
            self.signals[s] = {"symbol": s, **{k: v for k, v in ind.items() if k != "series"}, **sig,
                               "blacklisted": self.is_blacklisted(s), "updated": now_iso()}

    # ---------- position math ----------
    @staticmethod
    def unrealized(pos: dict, price: float) -> float:
        d = 1 if pos["side"] == "LONG" else -1
        return (price - pos["entry_price"]) * pos["qty"] * d

    def position_view(self, pos: dict) -> dict:
        price = self.market.prices.get(pos["symbol"], pos["entry_price"])
        pnl = self.unrealized(pos, price)
        return {**pos, "mark_price": price, "unrealized_pnl": round(pnl, 4), "roe_pct": round(pnl / pos["margin"] * 100, 2)}

    async def open_position(self, symbol: str, side: str, price: float, margin: float, strategy: str, reason: str, tp: float, sl: float, grid_key: str | None = None):
        lev = self.config["leverage"]
        fee = margin * lev * self.config["fee_pct"] / 100
        if margin < 5 or self.balance < margin + fee:
            await self.log("warn", f"Yetersiz bakiye, pozisyon açılamadı ({margin:.2f} USDT)", symbol)
            return None
        notional = margin * lev
        pos = {
            "id": str(uuid.uuid4()), "symbol": symbol, "side": side, "strategy": strategy,
            "entry_price": price, "qty": notional / price, "margin": margin, "leverage": lev, "notional": notional,
            "tp": tp, "sl": sl, "trailing_sl": None, "peak": price, "opened_at": now_iso(), "reason": reason,
            "fee_open": fee, "grid_key": grid_key,
        }
        self.balance -= margin + fee
        self.positions[pos["id"]] = pos
        await self.db.positions.insert_one(dict(pos))
        await self.save_state()
        await self.log("trade", f"{'▲ LONG' if side == 'LONG' else '▼ SHORT'} açıldı @ {price:g} · marj {margin:.2f} USDT · {lev}x · {reason}", symbol,
                       {"side": side, "price": price, "strategy": strategy})
        return pos

    async def close_position(self, pos_id: str, price: float, exit_reason: str):
        pos = self.positions.pop(pos_id, None)
        if not pos:
            return None
        gross = self.unrealized(pos, price)
        fee_close = price * pos["qty"] * self.config["fee_pct"] / 100
        net = gross - fee_close - pos["fee_open"]
        self.balance += pos["margin"] + gross - fee_close
        opened = datetime.fromisoformat(pos["opened_at"])
        trade = {
            **pos, "exit_price": price, "pnl": round(net, 4), "pnl_pct": round(net / pos["margin"] * 100, 2),
            "fee_total": round(fee_close + pos["fee_open"], 4), "closed_at": now_iso(), "exit_reason": exit_reason,
            "duration_sec": int((datetime.now(timezone.utc) - opened).total_seconds()),
        }
        self.trades.insert(0, trade)
        self.cooldowns[pos["symbol"]] = datetime.now(timezone.utc) + timedelta(seconds=self.config["cooldown_seconds"])
        if pos.get("grid_key") and pos["symbol"] in self.grids:
            self.grids[pos["symbol"]]["filled"] = [k for k in self.grids[pos["symbol"]]["filled"] if k != pos["grid_key"]]
        await self.db.positions.delete_one({"id": pos_id})
        await self.db.trades.insert_one(dict(trade))
        if pos["strategy"] == "multi":
            await self.track_streak(pos["symbol"], net)
        await self.save_state()
        sign = "+" if net >= 0 else ""
        await self.log("win" if net >= 0 else "loss", f"{pos['side']} kapatıldı @ {price:g} · {exit_reason} · PnL {sign}{net:.2f} USDT ({sign}{trade['pnl_pct']:.1f}%)",
                       pos["symbol"], {"pnl": net, "reason": exit_reason})
        return trade

    async def track_streak(self, symbol: str, net: float):
        n = self.config["blacklist_losses"]
        if net >= 0:
            self.loss_streak[symbol] = 0
            return
        self.loss_streak[symbol] = self.loss_streak.get(symbol, 0) + 1
        if n and self.loss_streak[symbol] >= n:
            mins = self.config["blacklist_minutes"]
            self.blacklist[symbol] = (datetime.now(timezone.utc) + timedelta(minutes=mins)).isoformat()
            await self.log("warn", f"KARA LİSTE · arka arkaya {n} zarar → {mins} dk çoklu sinyal işlemi askıya alındı", symbol)

    async def partial_close(self, pos: dict, price: float):
        frac = self.config["partial_tp_fraction"]
        qty_c, margin_c = pos["qty"] * frac, pos["margin"] * frac
        d = 1 if pos["side"] == "LONG" else -1
        gross = (price - pos["entry_price"]) * qty_c * d
        fee_close = price * qty_c * self.config["fee_pct"] / 100
        fee_open_c = pos["fee_open"] * frac
        net = gross - fee_close - fee_open_c
        self.balance += margin_c + gross - fee_close
        pos.update({"qty": pos["qty"] - qty_c, "margin": pos["margin"] - margin_c, "notional": pos["notional"] * (1 - frac),
                    "fee_open": pos["fee_open"] - fee_open_c, "partial_done": True, "sl": pos["entry_price"]})
        trade = {
            **pos, "qty": qty_c, "margin": margin_c, "exit_price": price, "pnl": round(net, 4),
            "pnl_pct": round(net / margin_c * 100, 2), "fee_total": round(fee_close + fee_open_c, 4),
            "closed_at": now_iso(), "exit_reason": "KISMİ TP", "id": str(uuid.uuid4()), "parent_id": pos["id"],
            "duration_sec": int((datetime.now(timezone.utc) - datetime.fromisoformat(pos["opened_at"])).total_seconds()),
        }
        self.trades.insert(0, trade)
        await self.db.positions.update_one({"id": pos["id"]}, {"$set": {k: pos[k] for k in ("qty", "margin", "notional", "fee_open", "partial_done", "sl")}})
        await self.db.trades.insert_one(dict(trade))
        await self.save_state()
        await self.log("win", f"KISMİ TP · pozisyonun %{frac * 100:g}'i kapatıldı @ {price:g} · +{net:.2f} USDT · SL girişe çekildi", pos["symbol"], {"pnl": net, "reason": "KISMİ TP"})

    # ---------- management ----------
    async def manage_positions(self, prices: dict[str, float]):
        cfg = self.config
        for pos in list(self.positions.values()):
            price = prices.get(pos["symbol"])
            if not price:
                continue
            long = pos["side"] == "LONG"
            d = 1 if long else -1
            pnl = self.unrealized(pos, price)
            pos["peak"] = max(pos["peak"], price) if long else min(pos["peak"], price)
            fav_pct = (pos["peak"] - pos["entry_price"]) / pos["entry_price"] * 100 * d

            if pnl <= -pos["margin"] * 0.95:
                await self.close_position(pos["id"], price, "LİKİDASYON"); continue
            if (long and price >= pos["tp"]) or (not long and price <= pos["tp"]):
                await self.close_position(pos["id"], price, "TAKE PROFIT"); continue
            if (long and price <= pos["sl"]) or (not long and price >= pos["sl"]):
                await self.close_position(pos["id"], price, "STOP LOSS"); continue

            if pos["strategy"] == "multi":
                if cfg["partial_tp"] and not pos.get("partial_done"):
                    half_tp = pos["entry_price"] + (pos["tp"] - pos["entry_price"]) * 0.5
                    if (long and price >= half_tp) or (not long and price <= half_tp):
                        await self.partial_close(pos, price)
                if cfg["trailing"] and fav_pct >= cfg["trailing_activation_pct"]:
                    dist = cfg["trailing_distance_pct"] / 100
                    new_sl = pos["peak"] * (1 - dist * d)
                    if pos["trailing_sl"] is None or (long and new_sl > pos["trailing_sl"]) or (not long and new_sl < pos["trailing_sl"]):
                        pos["trailing_sl"] = new_sl
                        await self.db.positions.update_one({"id": pos["id"]}, {"$set": {"trailing_sl": new_sl, "peak": pos["peak"]}})
                if pos["trailing_sl"] is not None and ((long and price <= pos["trailing_sl"]) or (not long and price >= pos["trailing_sl"])):
                    await self.close_position(pos["id"], price, "TRAILING STOP"); continue
                age = (datetime.now(timezone.utc) - datetime.fromisoformat(pos["opened_at"])).total_seconds() / 60
                if age >= cfg["max_hold_minutes"]:
                    await self.close_position(pos["id"], price, "SÜRE DOLDU"); continue
                sig = self.signals.get(pos["symbol"])
                if sig and sig["side"] and sig["side"] != pos["side"] and pnl > 0:
                    await self.close_position(pos["id"], price, "TERS SİNYAL"); continue

    async def evaluate_multi(self, prices: dict[str, float]):
        cfg = self.config
        if cfg["strategy"] not in ("multi", "both"):
            return
        now = datetime.now(timezone.utc)
        for symbol in cfg["symbols"]:
            if len(self.positions) >= cfg["max_open_positions"]:
                return
            if any(p["symbol"] == symbol and p["strategy"] == "multi" for p in self.positions.values()):
                continue
            if self.cooldowns.get(symbol) and self.cooldowns[symbol] > now:
                continue
            if self.is_blacklisted(symbol):
                continue
            sig, price = self.signals.get(symbol), prices.get(symbol)
            if not sig or not price or not sig["side"]:
                continue
            d = 1 if sig["side"] == "LONG" else -1
            tp_dist, sl_dist = price * cfg["tp_pct"] / 100, price * cfg["sl_pct"] / 100
            mode = "sabit"
            if cfg["atr_tp_sl"] and sig.get("atr"):
                tp_dist = min(max(sig["atr"] * cfg["atr_tp_mult"], price * 0.002), price * 0.015)
                sl_dist = min(max(sig["atr"] * cfg["atr_sl_mult"], price * 0.0015), price * 0.01)
                if tp_dist < sl_dist * 1.2:
                    tp_dist = sl_dist * 1.2
                mode = "ATR"
            tp = price + tp_dist * d
            sl = price - sl_dist * d
            margin = self.balance * cfg["risk_per_trade_pct"] / 100
            votes = " ".join(f"{k.upper()}{'+' if v > 0 else ''}{v:g}" for k, v in sig["votes"].items() if v)
            trend = f" · 15m {sig['htf_trend']}" if sig.get("htf_trend") else ""
            await self.open_position(symbol, sig["side"], price, margin, "multi",
                                     f"skor {sig['score']:+.1f} [{votes}]{trend} · ADX {sig.get('adx', 0):.0f} · {mode} TP/SL", tp, sl)

    async def evaluate_grid(self, prices: dict[str, float]):
        cfg = self.config
        if cfg["strategy"] not in ("grid", "both"):
            return
        g = cfg["grid"]
        for symbol in g["symbols"]:
            price = prices.get(symbol)
            if not price:
                continue
            state = self.grids.get(symbol)
            open_grid = [p for p in self.positions.values() if p["symbol"] == symbol and p["strategy"] == "grid"]
            band = (g["levels"] + 2) * g["spacing_pct"] / 100
            if not state or (not open_grid and abs(price - state["center"]) / state["center"] > band):
                state = {"center": price, "filled": [], **strategies.grid_levels(price, g["levels"], g["spacing_pct"])}
                self.grids[symbol] = state
                await self.save_state()
                await self.log("info", f"Grid kuruldu · merkez {price:g} · {g['levels']}x2 seviye · aralık {g['spacing_pct']}%", symbol)
                continue
            prev = self.last_prices.get(symbol, price)
            step = g["spacing_pct"] / 100
            margin = self.balance * g["size_pct"] / 100
            for i, lvl in enumerate(state["buy"]):
                key = f"B{i}"
                if key not in state["filled"] and prev > lvl >= price and len(self.positions) < cfg["max_open_positions"]:
                    pos = await self.open_position(symbol, "LONG", price, margin, "grid", f"grid alım seviyesi {i + 1}",
                                                   price * (1 + step), state["center"] * (1 - band), key)
                    if pos:
                        state["filled"].append(key)
            for i, lvl in enumerate(state["sell"]):
                key = f"S{i}"
                if key not in state["filled"] and prev < lvl <= price and len(self.positions) < cfg["max_open_positions"]:
                    pos = await self.open_position(symbol, "SHORT", price, margin, "grid", f"grid satım seviyesi {i + 1}",
                                                   price * (1 - step), state["center"] * (1 + band), key)
                    if pos:
                        state["filled"].append(key)

    async def snapshot_equity(self, prices: dict[str, float]):
        now = datetime.now(timezone.utc)
        if self._last_equity_ts and (now - self._last_equity_ts).total_seconds() < 20:
            return
        self._last_equity_ts = now
        eq = self.compute_equity(prices)
        point = {"t": now.isoformat(), "equity": round(eq, 2), "balance": round(self.balance, 2)}
        self.equity.append(point)
        self.equity = self.equity[-3000:]
        await self.db.equity.insert_one(dict(point))

    def compute_equity(self, prices: dict[str, float] | None = None) -> float:
        prices = prices or self.market.prices
        return self.balance + sum(p["margin"] + self.unrealized(p, prices.get(p["symbol"], p["entry_price"])) for p in self.positions.values())

    # ---------- stats ----------
    @staticmethod
    def _perf(trades: list[dict]) -> dict:
        wins = [t for t in trades if t["pnl"] > 0]
        gw = sum(t["pnl"] for t in wins)
        gl = abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0))
        return {
            "trades": len(trades), "wins": len(wins), "losses": len(trades) - len(wins),
            "pnl": round(sum(t["pnl"] for t in trades), 2),
            "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
            "profit_factor": round(gw / gl, 2) if gl else (round(gw, 2) if gw else 0.0),
            "avg_pnl": round(sum(t["pnl"] for t in trades) / len(trades), 2) if trades else 0.0,
        }

    def uptime(self) -> dict:
        now = datetime.now(timezone.utc)
        session = (now - datetime.fromisoformat(self.session_started_at)).total_seconds() if self.running else 0
        return {
            "first_started_at": self.first_started_at,
            "session_started_at": self.session_started_at if self.running else None,
            "session_sec": int(session),
            "total_active_sec": int(self.total_active_sec),
            "calendar_days": round((now - datetime.fromisoformat(self.first_started_at)).total_seconds() / 86400, 1) if self.first_started_at else 0,
        }

    def protection(self) -> dict:
        eq = self.compute_equity()
        start = self.day.get("start_equity") or eq
        return {
            "daily_loss_limit_pct": self.config["daily_loss_limit_pct"],
            "day_start_equity": start,
            "day_change_pct": round((eq - start) / start * 100, 2) if start else 0.0,
            "halted": self.day.get("halted", False),
            "blacklist": [{"symbol": s, "until": u, "streak": self.loss_streak.get(s, 0)} for s, u in list(self.blacklist.items()) if self.is_blacklisted(s)],
            "loss_streak": self.loss_streak,
        }

    def stats(self) -> dict:
        today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        wins = [t for t in self.trades if t["pnl"] > 0]
        losses = [t for t in self.trades if t["pnl"] <= 0]
        today_trades = [t for t in self.trades if t["closed_at"] >= today]
        gross_win = sum(t["pnl"] for t in wins)
        gross_loss = abs(sum(t["pnl"] for t in losses))
        equity = self.compute_equity()
        unreal = sum(self.unrealized(p, self.market.prices.get(p["symbol"], p["entry_price"])) for p in self.positions.values())
        init = float(self.config["initial_balance"])
        return {
            "balance": round(self.balance, 2),
            "equity": round(equity, 2),
            "unrealized_pnl": round(unreal, 2),
            "realized_pnl": round(sum(t["pnl"] for t in self.trades), 2),
            "today_pnl": round(sum(t["pnl"] for t in today_trades), 2),
            "today_trades": len(today_trades),
            "total_trades": len(self.trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / len(self.trades) * 100, 1) if self.trades else 0.0,
            "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else (round(gross_win, 2) if gross_win else 0.0),
            "roi_pct": round((equity - init) / init * 100, 2),
            "best_trade": round(max((t["pnl"] for t in self.trades), default=0.0), 2),
            "worst_trade": round(min((t["pnl"] for t in self.trades), default=0.0), 2),
            "open_positions": len(self.positions),
            "margin_used": round(sum(p["margin"] for p in self.positions.values()), 2),
            "by_strategy": {
                "grid": self._perf([t for t in self.trades if t["strategy"] == "grid"]),
                "multi": self._perf([t for t in self.trades if t["strategy"] == "multi"]),
            },
            "uptime": self.uptime(),
            "protection": self.protection(),
        }
