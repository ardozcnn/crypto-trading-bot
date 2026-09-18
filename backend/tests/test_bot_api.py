"""Backend API tests for Binance Futures Testnet paper-trading bot."""
import os
import time
import datetime as dt
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback to reading frontend .env
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")

API = f"{BASE_URL}/api"
TEST_START_ISO = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


# ---------- Bot status: by_strategy, uptime, protection, config filters ----------
class TestBotStatus:
    def test_status_shape(self):
        r = requests.get(f"{API}/bot/status", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["running"] in (True, False)
        stats = data["stats"]
        # by_strategy
        assert "by_strategy" in stats
        for strat in ("grid", "multi"):
            s = stats["by_strategy"][strat]
            for k in ("trades", "wins", "losses", "pnl", "win_rate", "profit_factor", "avg_pnl"):
                assert k in s, f"{strat} missing {k}"
        # uptime
        up = stats["uptime"]
        for k in ("first_started_at", "session_started_at", "session_sec", "total_active_sec", "calendar_days"):
            assert k in up, f"uptime missing {k}"
        # protection
        pr = stats["protection"]
        for k in ("daily_loss_limit_pct", "day_start_equity", "day_change_pct", "halted", "blacklist", "loss_streak"):
            assert k in pr, f"protection missing {k}"
        # config filters
        cfg = data["config"]
        f = cfg["filters"]
        for k in ("htf_trend", "htf_timeframe", "htf_ema", "adx_min", "volume_min_ratio"):
            assert k in f, f"filters missing {k}"
        for k in ("atr_tp_sl", "atr_tp_mult", "atr_sl_mult", "partial_tp", "partial_tp_fraction",
                  "daily_loss_limit_pct", "blacklist_losses", "blacklist_minutes"):
            assert k in cfg, f"config missing {k}"


# ---------- Market signals shape ----------
class TestMarketSignals:
    def test_signals_shape(self):
        r = requests.get(f"{API}/market/signals", timeout=20)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) >= 1
        vol_ratios = []
        for item in arr:
            for k in ("adx", "vol_ratio", "htf_trend", "raw_side", "blocked", "blacklisted"):
                assert k in item, f"{item.get('symbol')} missing {k}"
            assert item["htf_trend"] in ("UP", "DOWN", "FLAT")
            assert isinstance(item["blacklisted"], bool)
            assert item["blocked"] is None or isinstance(item["blocked"], str)
            assert item["vol_ratio"] > 0, f"vol_ratio must be >0 for {item['symbol']}"
            assert 0.05 <= item["vol_ratio"] <= 20, f"vol_ratio out of expected range for {item['symbol']}: {item['vol_ratio']}"
            vol_ratios.append(item["vol_ratio"])
        # Ensure vol_ratio is not ~0 for all symbols
        assert max(vol_ratios) > 0.2, "All vol_ratio values are ~0 - bug!"


# ---------- Config PUT / restore ----------
class TestBotConfig:
    def test_get_config(self):
        r = requests.get(f"{API}/bot/config", timeout=10)
        assert r.status_code == 200
        cfg = r.json()
        assert "filters" in cfg

    def test_patch_and_restore(self):
        # Save originals
        original = requests.get(f"{API}/bot/config", timeout=10).json()
        orig_adx = original["filters"]["adx_min"]
        orig_tp = original["atr_tp_mult"]
        orig_dll = original["daily_loss_limit_pct"]

        try:
            patch = {"filters": {"adx_min": 25}, "atr_tp_mult": 2.0, "daily_loss_limit_pct": 4}
            r = requests.put(f"{API}/bot/config", json=patch, timeout=10)
            assert r.status_code == 200
            cfg = requests.get(f"{API}/bot/config", timeout=10).json()
            assert cfg["filters"]["adx_min"] == 25
            assert cfg["atr_tp_mult"] == 2.0
            assert cfg["daily_loss_limit_pct"] == 4
        finally:
            # Restore to requested defaults
            restore = {
                "filters": {"adx_min": 20},
                "atr_tp_mult": 1.5,
                "daily_loss_limit_pct": 3,
            }
            rr = requests.put(f"{API}/bot/config", json=restore, timeout=10)
            assert rr.status_code == 200
            cfg = requests.get(f"{API}/bot/config", timeout=10).json()
            assert cfg["filters"]["adx_min"] == 20
            assert cfg["atr_tp_mult"] == 1.5
            assert cfg["daily_loss_limit_pct"] == 3


# ---------- Logs: no errors newer than test start; bot still running ----------
class TestBotLogsAndRunning:
    def test_no_error_logs_and_running(self):
        # give it a bit of runtime
        time.sleep(3)
        r = requests.get(f"{API}/logs", timeout=10)
        assert r.status_code == 200
        logs = r.json()
        assert isinstance(logs, list)
        recent_errors = []
        for log in logs:
            lvl = str(log.get("level", "")).lower()
            ts = log.get("ts") or log.get("time") or log.get("timestamp") or ""
            if lvl == "error" and ts and ts > TEST_START_ISO:
                recent_errors.append(log)
        assert not recent_errors, f"Found error logs after test start: {recent_errors[:3]}"

        # ensure bot still running
        status = requests.get(f"{API}/bot/status", timeout=10).json()
        assert status["running"] is True, "Bot should remain running"
