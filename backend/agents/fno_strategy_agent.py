from typing import Dict


def run_fno_strategy_agent(candidate: Dict) -> Dict:
    segment = str(candidate.get("segment", "")).upper()
    multi_leg = candidate.get("multi_leg", [])

    if segment == "F&O":
        has_hedge = isinstance(multi_leg, list) and len(multi_leg) > 1
        return {
            "ok": True,
            "score": 0.86 if has_hedge else 0.79,
            "details": {
                "oi_support": "aligned",
                "multi_leg_hedged": has_hedge,
            },
        }

    return {
        "ok": True,
        "score": 0.78,
        "details": {"segment": "CASH_STOCK", "oi_support": "not_applicable"},
    }
