from typing import Dict


def run_sentiment_news_agent(candidate: Dict) -> Dict:
    symbol = str(candidate.get("symbol", "")).strip()
    if not symbol:
        return {"ok": False, "score": 0.0, "reason": "Missing symbol"}

    return {
        "ok": True,
        "score": 0.77,
        "sentiment": {
            "market_bias": "constructive",
            "event_shock_risk": "low",
        },
    }
