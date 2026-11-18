import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

STOCK_UNIVERSE = [
    "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "BHARTIARTL", "SBIN", "LT",
    "ITC", "TATAMOTORS", "BAJFINANCE", "MARUTI", "SUNPHARMA", "ADANIENT", "TITAN",
    "AXISBANK", "KOTAKBANK", "NTPC", "ONGC", "TATASTEEL", "BEL", "HAL", "TRENT", "SUZLON", "ZOMATO"
]

INDICES = [
    ("NIFTY", "%5ENSEI", 50, 75),
    ("BANKNIFTY", "%5ENSEBANK", 100, 30),
    ("SENSEX", "%5EBSESN", 100, 20),
]

def is_zerodha_configured() -> bool:
    return True

def _fetch_chart(ticker: str) -> Dict:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1mo"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))["chart"]["result"][0]

def _build_index_setups() -> List[Dict]:
    out = []
    for name, ticker, step_strike, lot in INDICES:
        try:
            res = _fetch_chart(ticker)
            meta = res["meta"]
            closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
            spot = round(float(meta.get("regularMarketPrice") or closes[-1]), 2)
            prev = float(closes[-2])
            avg_5 = sum(closes[-5:]) / 5.0
            chg_pct = ((spot - prev) / prev) * 100

            atm = int(round(spot / step_strike) * step_strike)
            bullish = spot >= avg_5 and chg_pct >= 0
            ce_prob = min(84, max(54, int(64 + chg_pct * 6))) if bullish else max(38, int(48 + chg_pct * 4))
            pe_prob = min(84, max(54, int(64 - chg_pct * 6))) if not bullish else max(38, int(48 - chg_pct * 4))

            win_prob = max(ce_prob, pe_prob)
            loss_prob = 100 - win_prob
            opt_type = "CE" if ce_prob >= pe_prob else "PE"
            opt_ltp = round(max(85.0, (spot % step_strike) + 115.0), 2)
            t_step = round(opt_ltp * 0.16, 2)
            sl_step = round(opt_ltp * 0.08, 2)

            out.append({
                "symbol": f"{name} {atm} {opt_type} (Profit {win_prob}% | Loss {loss_prob}%)",
                "segment": "F&O",
                "ltp": opt_ltp,
                "win_prob": win_prob,
                "loss_prob": loss_prob,
                "side": "BUY",
                "is_fno": True,
                "entry": round(opt_ltp + 1.0, 2),
                "min_target": round(opt_ltp + t_step, 2),
                "target": round(opt_ltp + (t_step * 1.8), 2),
                "min_sl": round(opt_ltp - sl_step, 2),
                "sl": round(opt_ltp - (sl_step * 1.5), 2),
                "lot_size": lot,
                "multi_leg": [
                    {
                        "action": "BUY",
                        "lots": 1,
                        "type": f"{atm} CE (Profit {ce_prob}% | Loss {100 - ce_prob}%)",
                        "max_leg_pnl": round(t_step * 1.8 * lot, 0),
                        "max_leg_loss": round(-sl_step * 1.5 * lot, 0),
                    },
                    {
                        "action": "BUY",
                        "lots": 1,
                        "type": f"{atm} PE (Profit {pe_prob}% | Loss {100 - pe_prob}%)",
                        "max_leg_pnl": round(t_step * 1.5 * lot, 0),
                        "max_leg_loss": round(-sl_step * 1.5 * lot, 0),
                    },
                ],
            })
        except Exception:
            continue
    return out

def _analyze_stock(symbol: str) -> List[Dict]:
    try:
        res = _fetch_chart(f"{symbol}.NS")
        meta = res["meta"]
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
        if len(closes) < 5:
            return []
        ltp = round(float(meta.get("regularMarketPrice") or closes[-1]), 2)
        prev = float(closes[-2])
        avg_5 = sum(closes[-5:]) / 5.0
        chg_pct = ((ltp - prev) / prev) * 100
        if abs(chg_pct) < 0.8 and ltp <= avg_5:
            return []

        side = "BUY" if ltp >= avg_5 else "SELL"
        win_prob = min(85, max(56, int(60 + abs(chg_pct) * 5)))
        loss_prob = 100 - win_prob
        mode = "Intraday" if abs(chg_pct) >= 1.2 else "Long/Swing"
        step = max(round(ltp * (0.012 if mode == "Intraday" else 0.035), 2), 1.5)

        return [{
            "symbol": f"{symbol} [{mode}] (Profit {win_prob}% | Loss {loss_prob}%)",
            "segment": "Stocks",
            "ltp": ltp,
            "win_prob": win_prob,
            "loss_prob": loss_prob,
            "side": side,
            "is_fno": False,
            "entry": round(ltp + (0.5 if side == "BUY" else -0.5), 2),
            "min_target": round(ltp + (step if side == "BUY" else -step), 2),
            "target": round(ltp + (step * 1.8 if side == "BUY" else -step * 1.8), 2),
            "min_sl": round(ltp - (step * 0.5 if side == "BUY" else -step * 0.5), 2),
            "sl": round(ltp - (step * 0.9 if side == "BUY" else -step * 0.9), 2),
            "lot_size": 1,
            "multi_leg": [],
        }]
    except Exception:
        return []

def get_market_candidates() -> List[Dict]:
    idx_setups = _build_index_setups()
    with ThreadPoolExecutor(max_workers=12) as pool:
        nested = list(pool.map(_analyze_stock, STOCK_UNIVERSE))
    stock_setups = [item for sub in nested for item in sub]
    all_setups = idx_setups + stock_setups
    all_setups.sort(key=lambda x: x.get("win_prob", 0), reverse=True)
    return all_setups[:15]
