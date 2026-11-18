from typing import Dict, List
from config import ZERODHA_ACCESS_TOKEN, ZERODHA_API_KEY


def is_zerodha_configured() -> bool:
    return bool(ZERODHA_API_KEY.strip() and ZERODHA_ACCESS_TOKEN.strip())


def get_market_candidates() -> List[Dict]:
    """
    Returns market candidate setups for sub-agent evaluation.
    Uses clean sample setups when Zerodha API credentials are not yet set,
    and can be wired directly to Kite Connect live quotes/candles when ready.
    """
    return [
        {
            "symbol": "NIFTY 24650 CE",
            "segment": "F&O",
            "ltp": 142.50,
            "side": "BUY",
            "is_fno": True,
            "entry": 143.00,
            "min_target": 152.00,
            "target": 164.00,
            "min_sl": 137.50,
            "sl": 132.00,
            "lot_size": 75,
            "multi_leg": [
                {
                    "action": "BUY",
                    "lots": 2,
                    "type": "24650 CE",
                    "max_leg_pnl": 3150.0,
                    "max_leg_loss": -1650.0,
                },
                {
                    "action": "BUY",
                    "lots": 1,
                    "type": "24450 PE",
                    "max_leg_pnl": 950.0,
                    "max_leg_loss": -600.0,
                },
            ],
        },
        {
            "symbol": "RELIANCE",
            "segment": "Stocks",
            "ltp": 1348.00,
            "side": "BUY",
            "is_fno": False,
            "entry": 1349.00,
            "min_target": 1358.00,
            "target": 1368.50,
            "min_sl": 1342.00,
            "sl": 1336.00,
            "lot_size": 1,
            "multi_leg": [],
        },
        {
            "symbol": "BANKNIFTY 52400 PE",
            "segment": "F&O",
            "ltp": 218.00,
            "side": "BUY",
            "is_fno": True,
            "entry": 219.00,
            "min_target": 232.00,
            "target": 248.00,
            "min_sl": 211.00,
            "sl": 203.00,
            "lot_size": 30,
            "multi_leg": [],
        },
    ]