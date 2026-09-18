import numpy as np
import pandas as pd


def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    return out.fillna(50)


def macd(series: pd.Series, fast: int, slow: int, signal: int):
    line = ema(series, fast) - ema(series, slow)
    sig = ema(line, signal)
    return line, sig, line - sig


def bollinger(series: pd.Series, period: int, std: float):
    mid = series.rolling(period).mean()
    dev = series.rolling(period).std(ddof=0)
    return mid, mid + std * dev, mid - std * dev


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    prev_close = df["c"].shift(1)
    tr = pd.concat(
        [df["h"] - df["l"], (df["h"] - prev_close).abs(), (df["l"] - prev_close).abs()], axis=1
    ).max(axis=1)
    return tr.ewm(alpha=1 / period, adjust=False).mean()


def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    up = df["h"].diff()
    down = -df["l"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = atr(df, period)
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / tr.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / tr.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / period, adjust=False).mean().fillna(0)


def htf_trend(klines: list[dict], ema_period: int = 50) -> dict:
    df = pd.DataFrame(klines)
    e = ema(df["c"], ema_period)
    last, slope_ref = float(e.iloc[-1]), float(e.iloc[-4])
    close = float(df["c"].iloc[-1])
    slope_pct = (last - slope_ref) / slope_ref * 100
    if close > last and slope_pct > -0.02:
        trend = "UP"
    elif close < last and slope_pct < 0.02:
        trend = "DOWN"
    else:
        trend = "FLAT"
    return {"trend": trend, "ema": last, "close": close, "slope_pct": round(slope_pct, 4), "adx": round(float(adx(df, 14).iloc[-1]), 2)}


def compute(klines: list[dict], p: dict) -> dict:
    df = pd.DataFrame(klines)
    c = df["c"]
    adx_series = adx(df, 14)
    vol_avg = df["v"].iloc[-22:-2].mean()
    vol_ratio = float(df["v"].iloc[-2] / vol_avg) if vol_avg and not np.isnan(vol_avg) else 1.0
    df["ema_fast"] = ema(c, p["ema_fast"])
    df["ema_slow"] = ema(c, p["ema_slow"])
    df["rsi"] = rsi(c, p["rsi_period"])
    df["macd"], df["macd_signal"], df["macd_hist"] = macd(c, p["macd_fast"], p["macd_slow"], p["macd_signal"])
    df["bb_mid"], df["bb_upper"], df["bb_lower"] = bollinger(c, p["bb_period"], p["bb_std"])
    df["atr"] = atr(df, 14)
    df = df.replace({np.nan: None})
    last, prev = df.iloc[-1], df.iloc[-2]
    width = (last["bb_upper"] - last["bb_lower"]) if last["bb_upper"] is not None else None
    pct_b = ((last["c"] - last["bb_lower"]) / width) if width else 0.5
    return {
        "series": df.to_dict(orient="records"),
        "close": float(last["c"]),
        "rsi": float(last["rsi"]),
        "rsi_prev": float(prev["rsi"]),
        "macd_hist": float(last["macd_hist"]),
        "macd_hist_prev": float(prev["macd_hist"]),
        "macd": float(last["macd"]),
        "macd_signal": float(last["macd_signal"]),
        "bb_upper": last["bb_upper"],
        "bb_lower": last["bb_lower"],
        "bb_mid": last["bb_mid"],
        "pct_b": float(pct_b),
        "ema_fast": float(last["ema_fast"]),
        "ema_slow": float(last["ema_slow"]),
        "ema_fast_prev": float(prev["ema_fast"]),
        "ema_slow_prev": float(prev["ema_slow"]),
        "atr": float(last["atr"]) if last["atr"] is not None else 0.0,
        "adx": round(float(adx_series.iloc[-1]), 2),
        "vol_ratio": round(vol_ratio, 2),
    }
