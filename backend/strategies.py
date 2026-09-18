def multi_signal(ind: dict, p: dict, min_score: float) -> dict:
    votes = {}
    r, rp = ind["rsi"], ind["rsi_prev"]
    if r < p["rsi_buy"]:
        votes["rsi"] = 1
    elif r > p["rsi_sell"]:
        votes["rsi"] = -1
    elif rp < 50 <= r:
        votes["rsi"] = 0.5
    elif rp > 50 >= r:
        votes["rsi"] = -0.5
    else:
        votes["rsi"] = 0

    h, hp = ind["macd_hist"], ind["macd_hist_prev"]
    if hp <= 0 < h:
        votes["macd"] = 1
    elif hp >= 0 > h:
        votes["macd"] = -1
    elif h > 0 and h > hp:
        votes["macd"] = 0.5
    elif h < 0 and h < hp:
        votes["macd"] = -0.5
    else:
        votes["macd"] = 0

    pb = ind["pct_b"]
    if pb <= 0:
        votes["bb"] = 1
    elif pb >= 1:
        votes["bb"] = -1
    elif pb < 0.2:
        votes["bb"] = 0.5
    elif pb > 0.8:
        votes["bb"] = -0.5
    else:
        votes["bb"] = 0

    ef, es, c = ind["ema_fast"], ind["ema_slow"], ind["close"]
    crossed_up = ind["ema_fast_prev"] <= ind["ema_slow_prev"] and ef > es
    crossed_down = ind["ema_fast_prev"] >= ind["ema_slow_prev"] and ef < es
    if crossed_up:
        votes["ema"] = 1
    elif crossed_down:
        votes["ema"] = -1
    elif ef > es and c > ef:
        votes["ema"] = 0.5
    elif ef < es and c < ef:
        votes["ema"] = -0.5
    else:
        votes["ema"] = 0

    score = sum(votes.values())
    side = "LONG" if score >= min_score else "SHORT" if score <= -min_score else None
    return {"score": round(score, 2), "votes": votes, "side": side, "confidence": round(min(abs(score) / 4, 1), 2)}


def grid_levels(center: float, levels: int, spacing_pct: float) -> dict:
    step = spacing_pct / 100
    return {
        "buy": [round(center * (1 - i * step), 8) for i in range(1, levels + 1)],
        "sell": [round(center * (1 + i * step), 8) for i in range(1, levels + 1)],
    }
