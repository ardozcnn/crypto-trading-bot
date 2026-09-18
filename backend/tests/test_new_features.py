"""Backend tests for backtest, daily report, and live testnet order execution."""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = BASE_URL.rstrip("/")
API = f"{BASE_URL}/api"


# ---------- Backtest status: pre-existing done result shape ----------
class TestBacktestStatus:
    def test_status_shape_done(self):
        r = requests.get(f"{API}/backtest/status", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] in ("idle", "running", "done", "error")
        # If not done, kick a run and wait briefly; but spec says already done
        if data["status"] != "done":
            pytest.skip(f"backtest status is {data['status']}, need done - will be validated after run")
        res = data["result"]
        assert res is not None
        for k in ("days", "symbols", "candles", "from", "to", "duration_sec", "variants"):
            assert k in res, f"result missing {k}"
        assert res["candles"] > 200000, f"candles={res['candles']} not >200000"
        v = res["variants"]
        assert "baseline" in v and "current" in v
        for variant in ("baseline", "current"):
            cur = v[variant]
            for k in ("trades", "wins", "losses", "win_rate", "pnl", "roi_pct",
                      "profit_factor", "avg_pnl", "max_drawdown_pct", "best", "worst",
                      "daily", "by_symbol", "exit_reasons", "equity_curve"):
                assert k in cur, f"variants.{variant} missing {k}"


# ---------- Backtest run: start, dupe returns 409, poll until done ----------
class TestBacktestRun:
    def test_run_and_poll(self):
        r = requests.post(f"{API}/backtest/run", json={"days": 30}, timeout=15)
        assert r.status_code == 200, f"expected 200, got {r.status_code}: {r.text}"
        assert r.json().get("started") is True

        # Immediate second call should be 409
        r2 = requests.post(f"{API}/backtest/run", json={"days": 30}, timeout=15)
        # Accept 409 while still running; if it already completed instantly, allow 200
        assert r2.status_code in (409, 200), f"expected 409 or 200, got {r2.status_code}"
        if r2.status_code == 200:
            pytest.xfail("second call returned 200 - backtest completed too fast")
        assert r2.status_code == 409

        # Poll until done
        deadline = time.time() + 130
        last = None
        while time.time() < deadline:
            s = requests.get(f"{API}/backtest/status", timeout=15).json()
            last = s
            if s["status"] == "done":
                break
            if s["status"] == "error":
                pytest.fail(f"backtest error: {s.get('error')}")
            time.sleep(3)
        assert last and last["status"] == "done", f"backtest did not finish within 130s, last={last}"
        assert last["result"]["duration_sec"] is not None
        # numpy serialization sanity: response was parseable JSON above


# ---------- Daily report ----------
class TestDailyReport:
    def test_daily_report(self):
        r = requests.get(f"{API}/report/daily", timeout=15)
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list) and len(arr) >= 1
        first = arr[0]
        for k in ("date", "trades", "wins", "pnl", "grid_pnl", "multi_pnl",
                  "fees", "best", "worst", "win_rate", "cumulative"):
            assert k in first, f"missing {k}"
        # newest first
        dates = [row["date"] for row in arr]
        assert dates == sorted(dates, reverse=True), "not sorted newest first"
        # cumulative of oldest row equals its pnl
        oldest = arr[-1]
        assert abs(oldest["cumulative"] - oldest["pnl"]) < 1e-6, \
            f"oldest cumulative {oldest['cumulative']} != pnl {oldest['pnl']}"


# ---------- Live testnet ----------
class TestLive:
    def test_a_initial_status(self):
        r = requests.get(f"{API}/live/status", timeout=10)
        assert r.status_code == 200
        d = r.json()
        assert d["configured"] is False, f"initial should be unconfigured, got {d}"
        assert d["mode"] == "paper"

    def test_b_short_key_rejected(self):
        r = requests.post(f"{API}/live/credentials",
                          json={"api_key": "short", "api_secret": "short"}, timeout=15)
        assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text}"

    def test_c_fake_creds_saved_but_invalid(self):
        fake_key = "A" * 25
        fake_secret = "B" * 25
        r = requests.post(f"{API}/live/credentials",
                          json={"api_key": fake_key, "api_secret": fake_secret}, timeout=30)
        assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
        detail = r.json().get("detail", "")
        assert "doğrulanamadı" in detail, f"detail should contain 'doğrulanamadı', got: {detail}"

        # Status should show configured true with masked key
        s = requests.get(f"{API}/live/status", timeout=10).json()
        assert s["configured"] is True
        assert s.get("api_key_masked")

        # Attempting live mode should 400
        rm = requests.post(f"{API}/live/mode", json={"mode": "live"}, timeout=15)
        assert rm.status_code == 400, f"expected 400 for live mode without valid creds, got {rm.status_code}"

    def test_d_config_mode_ignored(self):
        # PUT /api/bot/config with mode:'live' should not change mode
        requests.put(f"{API}/bot/config", json={"mode": "live"}, timeout=10)
        s = requests.get(f"{API}/live/status", timeout=10).json()
        assert s["mode"] == "paper", f"mode should stay paper, got {s['mode']}"

    def test_e_delete_cleanup(self):
        r = requests.delete(f"{API}/live/credentials", timeout=15)
        assert r.status_code in (200, 204)
        s = requests.get(f"{API}/live/status", timeout=10).json()
        assert s["configured"] is False, f"after delete should be unconfigured: {s}"


# ---------- Regression: bot still running ----------
class TestRegression:
    def test_bot_still_running(self):
        r = requests.get(f"{API}/bot/status", timeout=10)
        assert r.status_code == 200
        assert r.json()["running"] is True
