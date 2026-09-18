import hashlib
import hmac
import os
import time
from decimal import Decimal, ROUND_DOWN
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet

BASE_URL = os.environ["BINANCE_FUTURES_BASE_URL"]
fernet = Fernet(os.environ["CREDENTIALS_FERNET_KEY"].encode())


class LiveError(Exception):
    pass


class LiveClient:
    def __init__(self, db):
        self.db = db
        self.api_key: str | None = None
        self.api_secret: str | None = None
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=15)
        self.lot: dict[str, dict] = {}
        self.leverage_set: dict[str, int] = {}
        self.account: dict | None = None
        self.last_error: str | None = None

    async def load(self):
        doc = await self.db.credentials.find_one({"_id": "binance"})
        if doc:
            self.api_key = doc["api_key"]
            self.api_secret = fernet.decrypt(doc["api_secret"].encode()).decode()

    async def save(self, api_key: str, api_secret: str):
        await self.db.credentials.replace_one(
            {"_id": "binance"},
            {"_id": "binance", "api_key": api_key.strip(), "api_secret": fernet.encrypt(api_secret.strip().encode()).decode()},
            upsert=True,
        )
        self.api_key, self.api_secret = api_key.strip(), api_secret.strip()
        self.leverage_set, self.account, self.last_error = {}, None, None

    async def clear(self):
        await self.db.credentials.delete_one({"_id": "binance"})
        self.api_key = self.api_secret = None
        self.account, self.leverage_set = None, {}

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.api_secret)

    def masked_key(self) -> str | None:
        return f"{self.api_key[:6]}…{self.api_key[-4:]}" if self.api_key else None

    async def request(self, method: str, path: str, params: dict | None = None, signed: bool = True):
        p = {k: v for k, v in (params or {}).items() if v is not None}
        headers = {}
        if signed:
            if not self.configured:
                raise LiveError("API anahtarı tanımlı değil")
            p["timestamp"] = int(time.time() * 1000)
            p["recvWindow"] = 5000
            payload = urlencode({k: str(v).lower() if isinstance(v, bool) else str(v) for k, v in p.items()})
            p["signature"] = hmac.new(self.api_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
            headers["X-MBX-APIKEY"] = self.api_key
        r = await self.client.request(method, path, params=p, headers=headers)
        try:
            data = r.json()
        except ValueError:
            data = {"msg": r.text}
        if r.status_code >= 400:
            msg = data.get("msg") if isinstance(data, dict) else str(data)
            self.last_error = f"{r.status_code} {msg}"
            raise LiveError(self.last_error)
        return data

    async def lot_info(self, symbol: str) -> dict:
        if not self.lot:
            info = await self.request("GET", "/fapi/v1/exchangeInfo", signed=False)
            for s in info["symbols"]:
                f = next((x for x in s["filters"] if x["filterType"] == "LOT_SIZE"), None)
                if f:
                    self.lot[s["symbol"]] = {"step": Decimal(f["stepSize"]), "min": Decimal(f["minQty"]), "max": Decimal(f["maxQty"])}
        if symbol not in self.lot:
            raise LiveError(f"{symbol} testnet'te işlem görmüyor")
        return self.lot[symbol]

    async def normalize_qty(self, symbol: str, qty: float) -> str:
        lot = await self.lot_info(symbol)
        q = (Decimal(str(qty)) / lot["step"]).to_integral_value(rounding=ROUND_DOWN) * lot["step"]
        if q < lot["min"]:
            raise LiveError(f"Miktar minimumun altında ({q} < {lot['min']})")
        q = min(q, lot["max"])
        return format(q, "f").rstrip("0").rstrip(".") or "0"

    async def ensure_leverage(self, symbol: str, leverage: int):
        if self.leverage_set.get(symbol) != leverage:
            await self.request("POST", "/fapi/v1/leverage", {"symbol": symbol, "leverage": leverage})
            self.leverage_set[symbol] = leverage

    async def market_order(self, symbol: str, side: str, qty: float, reduce_only: bool = False, leverage: int | None = None) -> dict:
        if leverage and not reduce_only:
            await self.ensure_leverage(symbol, leverage)
        q = await self.normalize_qty(symbol, qty)
        res = await self.request("POST", "/fapi/v1/order", {
            "symbol": symbol, "side": side, "type": "MARKET", "quantity": q,
            "reduceOnly": reduce_only, "newOrderRespType": "RESULT",
        })
        executed = float(res.get("executedQty") or 0)
        avg = float(res.get("avgPrice") or 0)
        if executed <= 0 or avg <= 0:
            raise LiveError(f"Emir gerçekleşmedi: {res.get('status')}")
        return {"order_id": res.get("orderId"), "qty": executed, "price": avg, "status": res.get("status")}

    async def refresh_account(self) -> dict:
        bal = await self.request("GET", "/fapi/v2/balance")
        usdt = next((b for b in bal if b["asset"] == "USDT"), None)
        pos = await self.request("GET", "/fapi/v2/positionRisk")
        open_pos = [
            {"symbol": p["symbol"], "amt": float(p["positionAmt"]), "entry": float(p["entryPrice"]), "pnl": float(p["unRealizedProfit"]), "leverage": int(p["leverage"])}
            for p in pos if float(p["positionAmt"]) != 0
        ]
        self.account = {
            "wallet_balance": float(usdt["balance"]) if usdt else 0.0,
            "available": float(usdt["availableBalance"]) if usdt else 0.0,
            "unrealized_pnl": float(usdt["crossUnPnl"]) if usdt else 0.0,
            "positions": open_pos,
            "updated": int(time.time()),
        }
        self.last_error = None
        return self.account

    async def close(self):
        await self.client.aclose()
