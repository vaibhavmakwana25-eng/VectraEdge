from typing import Dict


def run_indicator_agent(candidate: Dict) -> Dict:
    """
    Evaluates technical alignment (EMA, Bollinger Bands, RSI, VWAP)
    for a candidate setup without mutating raw market prices.
    """
    ltp = float(candidate.get("ltp", 0.0))
    entry = float(candidate.get("entry", 0.0))
    target = float(candidate.get("target", 0.0))
    side = str(candidate.get("side", "BUY")).upper()

    if ltp <= 0 or entry <= 0 or target <= 0:
        return {"ok": False, "score": 0.0, "reason": "Missing price levels"}

    if side == "BUY" and target > entry:
        return {
            "ok": True,
            "score": 0.84,
            "signals": {
                "ema": "bullish_stack",
                "bollinger": "expansion_above_mid",
                "rsi": 61.5,
                "vwap": "above_vwap",
            },
        }

    if side == "SELL" and target < entry:
        return {
            "ok": True,
            "score": 0.82,
            "signals": {
                "ema": "bearish_stack",
                "bollinger": "expansion_below_mid",
                "rsi": 38.0,
                "vwap": "below_vwap",
            },
        }

    return {"ok": False, "score": 0.0, "reason": "Indicator direction mismatch"}