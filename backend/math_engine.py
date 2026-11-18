from dataclasses import dataclass
from typing import Dict, List


@dataclass
class LotPnLResult:
    lot_size: int
    max_profit: float
    min_profit: float
    max_loss: float
    min_loss: float
    net_charges_est: float


def calculate_profit_percent(entry: float, target: float, side: str = "BUY") -> float:
    if entry <= 0 or target <= 0:
        raise ValueError("Invalid entry or target price")

    if side.upper() == "BUY":
        pct = ((target - entry) / entry) * 100.0
    elif side.upper() == "SELL":
        pct = ((entry - target) / entry) * 100.0
    else:
        raise ValueError(f"Unsupported side: {side}")

    return round(pct, 2)


def estimate_charges(turnover: float, is_fno: bool = True) -> float:
    if turnover <= 0:
        return 0.0
    rate = 0.0012 if is_fno else 0.0015
    return round(max(40.0, turnover * rate), 2)


def calculate_one_lot_pnl(
    entry: float,
    target: float,
    min_target: float,
    sl: float,
    min_sl: float,
    lot_size: int,
    side: str = "BUY",
    is_fno: bool = True,
) -> LotPnLResult:
    if lot_size <= 0:
        raise ValueError("Lot size must be positive")

    if side.upper() == "BUY":
        if not (target > entry > sl):
            raise ValueError("Invalid BUY levels: require target > entry > sl")
        max_pts = target - entry
        min_pts = max(0.0, min_target - entry)
        max_loss_pts = entry - sl
        min_loss_pts = max(0.0, entry - min_sl)
    else:
        if not (target < entry < sl):
            raise ValueError("Invalid SELL levels: require target < entry < sl")
        max_pts = entry - target
        min_pts = max(0.0, entry - min_target)
        max_loss_pts = sl - entry
        min_loss_pts = max(0.0, min_sl - entry)

    turnover = entry * lot_size * 2
    charges = estimate_charges(turnover, is_fno=is_fno)

    max_profit = round((max_pts * lot_size) - charges, 2)
    min_profit = round(max(0.0, (min_pts * lot_size) - charges), 2)
    max_loss = round(-abs((max_loss_pts * lot_size) + charges), 2)
    min_loss = round(-abs((min_loss_pts * lot_size) + charges), 2)

    return LotPnLResult(
        lot_size=lot_size,
        max_profit=max_profit,
        min_profit=min_profit,
        max_loss=max_loss,
        min_loss=min_loss,
        net_charges_est=charges,
    )


def verify_multi_leg_strategy(legs: List[Dict]) -> Dict:
    if not legs:
        return {"valid": False, "reason": "No legs provided"}

    net_max_profit = 0.0
    net_max_loss = 0.0
    summary_parts = []

    for leg in legs:
        lots = int(leg["lots"])
        if lots <= 0:
            return {"valid": False, "reason": "Invalid leg lots"}
        summary_parts.append(f"{leg['action']} {lots} Lot {leg['type']}")
        net_max_profit += float(leg["max_leg_pnl"])
        net_max_loss += float(leg["max_leg_loss"])

    return {
        "valid": True,
        "summary": " + ".join(summary_parts),
        "max_profit": round(net_max_profit, 2),
        "max_loss": round(-abs(net_max_loss), 2),
    }