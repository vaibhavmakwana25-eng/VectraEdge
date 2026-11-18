from typing import Dict


def evaluate_combined_ai_signal(setup: Dict) -> Dict:
    symbol = str(setup.get("symbol") or "SETUP")
    side = str(setup.get("side") or "BUY").upper()
    ltp = float(setup.get("ltp") or 100.0)
    entry = float(setup.get("entry") or ltp)
    target = float(setup.get("target") or entry * 1.02)
    sl = float(setup.get("sl") or entry * 0.99)

    win_prob = float(setup.get("win_prob") or 65.0)
    bt_win = float(setup.get("backtest_win_rate") or win_prob)
    vol_ratio = float(setup.get("vol_ratio") or 1.15)
    rsi = float(setup.get("rsi") or 56.0)

    reward = abs(target - entry)
    risk = max(0.01, abs(entry - sl))
    rr_ratio = round(reward / risk, 2)

    # Price action & momentum scoring
    pa_score = 0.0
    if side == "BUY":
        pa_score += 8.0 if rsi >= 52 else (-6.0 if rsi < 45 else 2.0)
        pa_score += 8.0 if ltp >= entry * 0.995 else -4.0
    else:
        pa_score += 8.0 if rsi <= 52 else (-6.0 if rsi > 62 else 2.0)
        pa_score += 8.0 if ltp <= entry * 1.005 else -4.0

    vol_score = min(14.0, max(-6.0, (vol_ratio - 1.0) * 14.0))
    rr_score = 8.0 if rr_ratio >= 1.5 else (3.0 if rr_ratio >= 1.0 else -6.0)

    ai_score = int(min(95, max(35, round((bt_win * 0.45) + (win_prob * 0.35) + pa_score + vol_score + rr_score))))

    if ai_score >= 76 and rr_ratio >= 1.2:
        verdict = "STRONG AI PICK"
    elif ai_score >= 62:
        verdict = "AI BUY / WATCH"
    else:
        verdict = "CAUTION / WAIT"

    action_note = (
        f"Entry ₹{entry:.2f} | Exit Tgt ₹{target:.2f} | SL ₹{sl:.2f} (R:R 1:{rr_ratio}). "
        f"BT {bt_win:.0f}%, Vol {vol_ratio:.2f}x, RSI {rsi:.1f}."
    )

    return {
        "symbol": symbol,
        "ai_score": ai_score,
        "ai_verdict": verdict,
        "rr_ratio": rr_ratio,
        "ai_suggestion": f"{verdict} ({ai_score}/100) — {action_note}",
    }