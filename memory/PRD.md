# SCALPX Terminal — Binance Futures Testnet Paper Trading Bot

## Orijinal Problem
"gelişmiş bir binance test net ağı üzerinden çok kazandıracak trading botu yap"
- Mod: Paper trading (sanal 10.000 USDT), gerçek Binance Futures Testnet fiyatları (public fapi, API key yok)
- Stratejiler: Çoklu sinyal (RSI+MACD+BB+EMA skorlama) + Grid trading
- AI yok, tamamen teknik gösterge tabanlı. Kullanıcı dili: Türkçe.

## Mimari
- Backend: FastAPI `/app/backend` — `server.py` (API), `engine.py` (paper engine, 4sn döngü), `market.py` (Binance testnet), `indicators.py`, `strategies.py`
- Frontend: React `/app/frontend/src` — TopNav, TickerStrip, StatsCards, PerformancePanel, ChartPanel, SignalsPanel, ControlPanel, Positions/Trades/Equity, ActivityLog
- DB: MongoDB koleksiyonları `bot_state` (config, balance, running, grids, blacklist, loss_streak, day, first_started_at, total_active_sec), `positions`, `trades`, `logs`, `equity`
- API: `/api/bot/status|start|stop|reset|config`, `/api/positions`, `/api/trades`, `/api/logs`, `/api/equity`, `/api/market/symbols|prices|signals|klines`

## Tamamlananlar
- 2026-09-06 → 09-18: İlk iskelet (dashboard, paper engine, multi-signal + grid), Mongo kalıcılık.
- 2026-09-18 (bu oturum, testing_agent PASS — iteration_1.json):
  - Multi-sinyal filtreleri: 15m EMA-50 trend filtresi, ADX≥20, hacim oranı ≥0.8 (son kapanan mum), min_score 2.5
  - ATR tabanlı dinamik TP/SL (1.5×/1.0× ATR, clamp) + kısmi kâr alma (TP'nin yarısında %50, SL girişe)
  - Günlük zarar limiti (−%3 → o gün yeni işlem yok) + coin kara listesi (3 ardışık zarar → 120 dk, yalnız multi)
  - Grid: BTC/ETH/SOL/BNB, 6 seviye
  - Dashboard: Aktif Süre kartı (toplam/oturum/ilk başlatma), Grid vs Çoklu karşılaştırma, Risk Koruması kartı; ControlPanel "Filtreler" sekmesi + Risk alanları; SignalsPanel trend/ADX/hacim + engellenme sebebi
  - Uptime backfill: equity kayıtlarından geçmiş aktif süre hesaplandı (~15 saat)

## Veri Analizi (18 Eyl, 142 işlem)
Grid +1287 USDT (%90 kazanç) · Multi −358 USDT (%44) · SL toplam −858 · DOGE −397.

## Backlog
- P1: Deploy (7/24 kesintisiz çalışma) — kullanıcı istedi, platform Deploy butonu ile
- P1: Yeni filtrelerin etkisini 1-2 gün izleyip Grid vs Multi kartından karşılaştırma
- P2: Gerçek Binance Testnet emir gönderimi (API key/secret ile)
- P2: Backtest modülü (geçmiş kline üzerinde strateji testi)
- P2: Telegram bildirimleri (işlem açıldı/kapandı, günlük limit)
