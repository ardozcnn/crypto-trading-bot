import os
import httpx

BASE_URL = os.environ["BINANCE_FUTURES_BASE_URL"]

POPULAR_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT", "DOTUSDT", "LTCUSDT", "MATICUSDT",
    "TRXUSDT", "NEARUSDT", "ATOMUSDT", "UNIUSDT", "APTUSDT", "ARBUSDT",
    "OPUSDT", "SUIUSDT", "PEPEUSDT", "WIFUSDT", "1000SHIBUSDT", "FILUSDT",
]


class MarketData:
    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=10)
        self.prices: dict[str, float] = {}
        self.tickers: dict[str, dict] = {}
        self.klines: dict[str, list[dict]] = {}

    async def fetch_prices(self, symbols: set[str]) -> dict[str, float]:
        r = await self.client.get("/fapi/v1/ticker/price")
        r.raise_for_status()
        for x in r.json():
            if x["symbol"] in symbols:
                self.prices[x["symbol"]] = float(x["price"])
        return self.prices

    async def fetch_tickers(self, symbols: set[str]) -> dict[str, dict]:
        r = await self.client.get("/fapi/v1/ticker/24hr")
        r.raise_for_status()
        for x in r.json():
            s = x["symbol"]
            if s in symbols:
                self.tickers[s] = {
                    "symbol": s,
                    "price": float(x["lastPrice"]),
                    "change_pct": float(x["priceChangePercent"]),
                    "high": float(x["highPrice"]),
                    "low": float(x["lowPrice"]),
                    "volume": float(x["quoteVolume"]),
                }
        return self.tickers

    async def fetch_klines(self, symbol: str, interval: str = "1m", limit: int = 150, store: bool = True) -> list[dict]:
        r = await self.client.get(
            "/fapi/v1/klines", params={"symbol": symbol, "interval": interval, "limit": limit}
        )
        r.raise_for_status()
        data = [
            {"t": k[0], "o": float(k[1]), "h": float(k[2]), "l": float(k[3]), "c": float(k[4]), "v": float(k[5])}
            for k in r.json()
        ]
        if store:
            self.klines[symbol] = data
        return data

    async def close(self):
        await self.client.aclose()
