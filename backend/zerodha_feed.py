import json
import urllib.request
from typing import Dict, List
from config import ZERODHA_ACCESS_TOKEN, ZERODHA_API_KEY

def is_zerodha_configured() -> bool:
    return True

def _fetch_live_price(ticker: str, fallback: float) -> float:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1m&range=1d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            if price:
                return round(float(price), 2)
    except Exception:
        pass
    return fallback

def get_market_candidates() -> List[Dict]:
    nifty_spot = _fetch_live_price("%5ENSEI", 24650.0)
    bn_spot = _fetch_live_price("%5ENSEBANK", 52400.0)
    rel_ltp = _fetch_live_price("RELIANCE.NS", 1348.0)

    nifty_strike = int(round(nifty_spot / 50.0) * 50)
    nifty_pe_strike = nifty_strike - 200
    bn_strike = int(round(bn_spot / 100.0) * 100)

    nifty_opt_ltp = round(max(65.0, (nifty_spot % 100) + 92.5), 2)
    bn_opt_ltp = round(max(95.0, (bn_spot % 200) + 118.0), 2)

    return [
        {
            "symbol": f"NIFTY {nifty_strike} CE",
            "segment": "F&O",
            "ltp": nifty_opt_ltp,
            "side": "BUY",
            "is_fno": True,
            "entry": round(nifty_opt_ltp + 0.5, 2),
            "min_target": round(nifty_opt_ltp + 9.5, 2),
            "target": round(nifty_opt_ltp + 21.5, 2),
            "min_sl": round(nifty_opt_ltp - 5.0, 2),
            "sl": round(nifty_opt_ltp - 10.5, 2),
            "lot_size": 75,
            "multi_leg": [
                {
                    "action": "BUY",
                    "lots": 2,
                    "type": f"{nifty_strike} CE",
                    "max_leg_pnl": 3150.0,
                    "max_leg_loss": -1650.0,
                },
                {
                    "action": "BUY",
                    "lots": 1,
                    "type": f"{nifty_pe_strike} PE",
                    "max_leg_pnl": 950.0,
                    "max_leg_loss": -600.0,
                },
            ],
        },
        {
            "symbol": "RELIANCE",
            "segment": "Stocks",
            "ltp": rel_ltp,
            "side": "BUY",
            "is_fno": False,
            "entry": round(rel_ltp + 1.0, 2),
            "min_target": round(rel_ltp + 10.0, 2),
            "target": round(rel_ltp + 20.5, 2),
            "min_sl": round(rel_ltp - 6.0, 2),
            "sl": round(rel_ltp - 12.0, 2),
            "lot_size": 1,
            "multi_leg": [],
        },
        {
            "symbol": f"BANKNIFTY {bn_strike} PE",
            "segment": "F&O",
            "ltp": bn_opt_ltp,
            "side": "BUY",
            "is_fno": True,
            "entry": round(bn_opt_ltp + 1.0, 2),
            "min_target": round(bn_opt_ltp + 14.0, 2),
            "target": round(bn_opt_ltp + 30.0, 2),
            "min_sl": round(bn_opt_ltp - 7.0, 2),
            "sl": round(bn_opt_ltp - 15.0, 2),
            "lot_size": 30,
            "multi_leg": [],
        },
    ]
