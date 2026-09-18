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
- 2026-09-18 (oturum 2, testing_agent PASS — iteration_2.json):
  - Backtest modülü (`backtest.py`): 30 gün 1m mum, 6 parite, Eski (filtresiz) vs Yeni (mevcut config) multi-sinyal karşılaştırması; Mongo `backtests`; UI "Backtest" sekmesi (metrik tablosu, equity eğrisi, parite/çıkış sebebi kırılımı)
  - Günlük Rapor sekmesi (`/api/report/daily`): gün bazlı işlem/kazanç/grid-multi PnL/komisyon/kümülatif
  - Canlı Testnet emir altyapısı (`live.py`): Fernet ile şifreli API key saklama (`CREDENTIALS_FERNET_KEY` env), HMAC imzalı MARKET emir, reduce-only kapatma, LOT_SIZE yuvarlama, kaldıraç ayarı, hesap bakiyesi; `/api/live/*`; ControlPanel "Canlı" sekmesi, TopNav LIVE etiketi. Kullanıcı henüz key girmedi → paper modda.
  - Telegram bildirimi: kullanıcı VAZGEÇTİ.
  - İlk backtest bulgusu: eski multi ayarları 30 günde −5.325 USDT (1189 işlem); yeni filtreler −76 USDT (17 işlem). Multi strateji hâlâ kârlı değil → parametre taraması (memory/sweep.py → sweep_results.json)
- 2026-09-06 → 09-18: İlk iskelet (dashboard, paper engine, multi-signal + grid), Mongo kalıcılık.
- 2026-09-18 (bu oturum, testing_agent PASS — iteration_1.json):
  - Multi-sinyal filtreleri: 15m EMA-50 trend filtresi, ADX≥20, hacim oranı ≥0.8 (son kapanan mum), min_score 2.5
  - ATR tabanlı dinamik TP/SL (1.5×/1.0× ATR, clamp) + kısmi kâr alma (TP'nin yarısında %50, SL girişe)
  - Günlük zarar limiti (−%3 → o gün yeni işlem yok) + coin kara listesi (3 ardışık zarar → 120 dk, yalnız multi)
  - Grid: BTC/ETH/SOL/BNB, 6 seviye
  - Dashboard: Aktif Süre kartı (toplam/oturum/ilk başlatma), Grid vs Çoklu karşılaştırma, Risk Koruması kartı; ControlPanel "Filtreler" sekmesi + Risk alanları; SignalsPanel trend/ADX/hacim + engellenme sebebi
  - Uptime backfill: equity kayıtlarından geçmiş aktif süre hesaplandı (~15 saat)

- 2026-09-18 (oturum 3, Grid parametre optimizasyonu — canlı doğrulama YAPILDI):
  - `sweep_grid.py` çalıştırıldı: 297 kombinasyon, 101 pozitif. En iyi: spacing 0.5%, levels 4, trend_filter=True, adx_pause=35, atr_spacing_mult=1.5, tf 15m → 449 işlem, 91.1% WR, +4.306 USDT (30 gün), PF 2.89, DD 4.11%.
  - `engine.py` DEFAULT_CONFIG.grid güncellendi (yeni parametreler + 6 coin: BTC/ETH/SOL/BNB/XRP/DOGE) ve `evaluate_grid` trend_filter/adx_pause/atr_spacing_mult filtrelerini uygulayacak şekilde genişletildi. Varsayılan strateji `grid` yapıldı (multi 1m'de hâlâ zararlı).
  - Backtest tekrar çalıştırıldı: grid variant 451 işlem, 91.4% WR, +4.374 USDT, PF 2.89, DD 3.15% — sweep sonuçlarını doğruluyor.
  - Bot canlı çalışıyor: 8 açık grid pozisyon, +827 USDT toplam PnL (76.5% WR), Grid tek başına +1.197 USDT (87% WR, PF 4.43).

## Veri Analizi (18 Eyl, 142 işlem)
Grid +1287 USDT (%90 kazanç) · Multi −358 USDT (%44) · SL toplam −858 · DOGE −397.

## Backlog
- P1: Deploy (7/24 kesintisiz çalışma) — kullanıcı istedi, platform Deploy butonu ile
- P1: Yeni Grid parametreleriyle 24-48 saat izleyip WR/PF hedefini doğrula
- P2: Gerçek Binance Testnet emir gönderimi (kullanıcı API key/secret girdiğinde otomatik)
- P2: MongoDB'e trade/position kalıcı persist (in-memory state'in yanına)
- P2: Multi-sinyal stratejisini 15m TF'te tekrar tara ve profitable versiyonu bul
