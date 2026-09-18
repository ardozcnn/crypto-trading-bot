from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List
from contextlib import asynccontextmanager
import os
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

from engine import BotEngine  # noqa: E402
from market import POPULAR_SYMBOLS  # noqa: E402
from live import LiveError  # noqa: E402
from backtest import Backtester  # noqa: E402
import indicators  # noqa: E402

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]
engine = BotEngine(db)
backtester = Backtester(engine.market, db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await engine.load()
    await backtester.load_last()
    engine.start_loop()
    yield
    await engine.market.close()
    await engine.live.close()
    client.close()


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


class IndicatorConfig(BaseModel):
    rsi_period: Optional[int] = None
    rsi_buy: Optional[float] = None
    rsi_sell: Optional[float] = None
    ema_fast: Optional[int] = None
    ema_slow: Optional[int] = None
    bb_period: Optional[int] = None
    bb_std: Optional[float] = None
    macd_fast: Optional[int] = None
    macd_slow: Optional[int] = None
    macd_signal: Optional[int] = None


class GridConfig(BaseModel):
    levels: Optional[int] = None
    spacing_pct: Optional[float] = None
    size_pct: Optional[float] = None
    symbols: Optional[List[str]] = None


class FilterConfig(BaseModel):
    htf_trend: Optional[bool] = None
    htf_timeframe: Optional[str] = None
    htf_ema: Optional[int] = None
    adx_min: Optional[float] = None
    volume_min_ratio: Optional[float] = None


class ConfigPatch(BaseModel):
    mode: Optional[str] = None
    strategy: Optional[str] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None
    leverage: Optional[int] = None
    risk_per_trade_pct: Optional[float] = None
    max_open_positions: Optional[int] = None
    tp_pct: Optional[float] = None
    sl_pct: Optional[float] = None
    trailing: Optional[bool] = None
    trailing_activation_pct: Optional[float] = None
    trailing_distance_pct: Optional[float] = None
    max_hold_minutes: Optional[int] = None
    cooldown_seconds: Optional[int] = None
    min_score: Optional[float] = None
    initial_balance: Optional[float] = None
    atr_tp_sl: Optional[bool] = None
    atr_tp_mult: Optional[float] = None
    atr_sl_mult: Optional[float] = None
    partial_tp: Optional[bool] = None
    partial_tp_fraction: Optional[float] = None
    daily_loss_limit_pct: Optional[float] = None
    blacklist_losses: Optional[int] = None
    blacklist_minutes: Optional[int] = None
    filters: Optional[FilterConfig] = None
    indicators: Optional[IndicatorConfig] = None
    grid: Optional[GridConfig] = None


@api_router.get("/")
async def root():
    return {"message": "Binance Futures Testnet Paper Trading Bot API"}


@api_router.get("/bot/status")
async def bot_status():
    return {
        "running": engine.running,
        "mode": engine.mode_label(),
        "live": engine.is_live,
        "live_account": engine.live.account if engine.is_live else None,
        "config": engine.config,
        "stats": engine.stats(),
        "positions": [engine.position_view(p) for p in engine.positions.values()],
        "prices": engine.market.prices,
        "tickers": list(engine.market.tickers.values()),
        "grids": engine.grids,
    }


class CredentialsIn(BaseModel):
    api_key: str = Field(min_length=20)
    api_secret: str = Field(min_length=20)


class ModeIn(BaseModel):
    mode: str


class BacktestIn(BaseModel):
    days: int = Field(default=30, ge=1, le=60)


@api_router.get("/live/status")
async def live_status():
    return {
        "configured": engine.live.configured,
        "api_key_masked": engine.live.masked_key(),
        "mode": engine.config.get("mode", "paper"),
        "base_url": os.environ["BINANCE_FUTURES_BASE_URL"],
        "account": engine.live.account,
        "last_error": engine.live.last_error,
    }


@api_router.post("/live/credentials")
async def live_credentials(body: CredentialsIn):
    await engine.live.save(body.api_key, body.api_secret)
    try:
        account = await engine.live.refresh_account()
    except LiveError as e:
        raise HTTPException(400, f"Anahtar kaydedildi ama doğrulanamadı: {e}")
    await engine.log("info", f"Binance Testnet API anahtarı kaydedildi ({engine.live.masked_key()}) · cüzdan {account['wallet_balance']:.2f} USDT")
    return {"ok": True, "api_key_masked": engine.live.masked_key(), "account": account}


@api_router.delete("/live/credentials")
async def live_credentials_delete():
    if engine.config.get("mode") == "live":
        engine.config["mode"] = "paper"
        await engine.save_state()
    await engine.live.clear()
    await engine.log("warn", "Binance Testnet API anahtarı silindi · PAPER moduna dönüldü")
    return {"ok": True}


@api_router.post("/live/test")
async def live_test():
    try:
        return await engine.live.refresh_account()
    except LiveError as e:
        raise HTTPException(400, str(e))


@api_router.post("/live/mode")
async def live_mode(body: ModeIn):
    if body.mode not in ("paper", "live"):
        raise HTTPException(400, "mode must be paper | live")
    try:
        await engine.set_mode(body.mode)
    except LiveError as e:
        raise HTTPException(400, str(e))
    return {"mode": engine.config["mode"], "label": engine.mode_label()}


@api_router.get("/report/daily")
async def report_daily():
    return engine.daily_report()


@api_router.post("/backtest/run")
async def backtest_run(body: BacktestIn):
    if not backtester.start(engine.config, body.days):
        raise HTTPException(409, "Backtest zaten çalışıyor")
    return {"started": True, "days": body.days}


@api_router.get("/backtest/status")
async def backtest_status():
    return backtester.state


@api_router.post("/bot/start")
async def bot_start():
    await engine.start()
    return {"running": engine.running}


@api_router.post("/bot/stop")
async def bot_stop():
    await engine.stop()
    return {"running": engine.running}


@api_router.post("/bot/reset")
async def bot_reset():
    await engine.reset()
    return {"balance": engine.balance, "running": engine.running}


@api_router.get("/bot/config")
async def get_config():
    return engine.config


@api_router.put("/bot/config")
async def put_config(patch: ConfigPatch):
    data = patch.model_dump(exclude_none=True)
    data.pop("mode", None)
    if "strategy" in data and data["strategy"] not in ("multi", "grid", "both"):
        raise HTTPException(400, "strategy must be multi | grid | both")
    if "leverage" in data and not 1 <= data["leverage"] <= 125:
        raise HTTPException(400, "leverage must be 1-125")
    return await engine.update_config(data)


@api_router.get("/positions")
async def positions():
    return [engine.position_view(p) for p in engine.positions.values()]


@api_router.post("/positions/{pos_id}/close")
async def close_position(pos_id: str):
    pos = engine.positions.get(pos_id)
    if not pos:
        raise HTTPException(404, "Pozisyon bulunamadı")
    price = engine.market.prices.get(pos["symbol"], pos["entry_price"])
    return await engine.close_position(pos_id, price, "MANUEL")


@api_router.post("/positions/close-all")
async def close_all():
    closed = []
    for pid in list(engine.positions.keys()):
        pos = engine.positions[pid]
        price = engine.market.prices.get(pos["symbol"], pos["entry_price"])
        closed.append(await engine.close_position(pid, price, "MANUEL (TÜMÜ)"))
    return {"closed": len(closed)}


@api_router.get("/trades")
async def trades(limit: int = 100):
    return engine.trades[:limit]


@api_router.get("/logs")
async def logs(limit: int = 100):
    return engine.logs[:limit]


@api_router.get("/equity")
async def equity():
    return engine.equity


@api_router.get("/market/symbols")
async def symbols():
    return POPULAR_SYMBOLS


@api_router.get("/market/prices")
async def prices():
    return engine.market.prices


@api_router.get("/market/signals")
async def signals():
    return list(engine.signals.values())


@api_router.get("/market/klines")
async def klines(symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 120):
    try:
        data = await engine.market.fetch_klines(symbol, interval, max(limit, 60))
    except Exception as e:
        raise HTTPException(502, f"Binance veri hatası: {e}")
    ind = indicators.compute(data, engine.config["indicators"])
    return {"symbol": symbol, "interval": interval, "candles": ind["series"][-limit:], "grid": engine.grids.get(symbol)}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)
