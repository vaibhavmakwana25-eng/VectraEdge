import json
import math
import urllib.request
from typing import Dict, List


def fetch_historical_candles(ticker: str, interval: str = "1d", range_span: str = "6mo") -> Dict:
    enc = urllib.request.quote(ticker, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?interval={interval}&range={range_span}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=2.5) as resp:
        result = json.loads(resp.read().decode("utf-8"))["chart"]["result"][0]
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    opens = [float(x) for x in quote.get("open", []) if x is not None]
    highs = [float(x) for x in quote.get("high", []) if x is not None]
    lows = [float(x) for x in quote.get("low", []) if x is not None]
    closes = [float(x) for x in quote.get("close", []) if x is not None]
    vols = [float(x) for x in quote.get("volume", []) if x is not None]
    return {
        "opens": opens,
        "highs": highs,
        "lows": lows,
        "closes": closes,
        "volumes": vols,
        "ltp": float(result.get("meta", {}).get("regularMarketPrice") or (closes[-1] if closes else 0.0)),
    }


def calc_ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    k = 2.0 / (period + 1.0)
    out = [values[0]]
    for v in values[1:]:
        out.append(v * k + out[-1] * (1.0 - k))
    return out


def calc_rsi(closes: List[float], period: int = 14) -> List[float]:
    if len(closes) < 2:
        return [50.0] * len(closes)
    out = [50.0]
    gains, losses = [], []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(0.0, diff))
        losses.append(max(0.0, -diff))
        if i < period:
            out.append(50.0)
        else:
            ag = sum(gains[-period:]) / period
            al = (sum(losses[-period:]) / period) or 1e-6
            rs = ag / al
            out.append(round(100.0 - (100.0 / (1.0 + rs)), 2))
    return out


def calc_bollinger(closes: List[float], period: int = 20, mult: float = 2.0):
    if len(closes) < period:
        c = closes[-1] if closes else 100.0
        return c * 1.03, c, c * 0.97
    win = closes[-period:]
    mid = sum(win) / period
    var = sum((x - mid) ** 2 for x in win) / period
    sd = math.sqrt(var)
    return mid + mult * sd, mid, mid - mult * sd


def run_backtest_on_candles(symbol: str, candles: Dict, side: str = "BUY") -> Dict:
    closes = candles.get("closes", [])
    highs = candles.get("highs", [])
    lows = candles.get("lows", [])
    vols = candles.get("volumes", [])
    n = len(closes)

    if n < 15:
        return {
            "symbol": symbol,
            "side": side,
            "trades_tested": 0,
            "win_rate": 0,
            "vol_ratio": 0.0,
            "rsi": 50.0,
            "passed": False,
            "reason": "Insufficient historical candles",
        }

    ema20 = calc_ema(closes, 20)
    ema50 = calc_ema(closes, 50)
    rsi_series = calc_rsi(closes, 14)

    wins = 0
    losses = 0
    cum_ret_pct = 0.0

    for i in range(10, n - 1):
        vol_base = (sum(vols[max(0, i - 10):i]) / max(1, min(10, i))) if vols else 1.0
        vol_cur = vols[i] if i < len(vols) else vol_base
        vol_r = (vol_cur / vol_base) if vol_base > 0 else 1.0

        # Rolling VWAP proxy using typical price & volume when available
        start_w = max(0, i - 14)
        tp_sum = 0.0
        v_sum = 0.0
        for j in range(start_w, i + 1):
            h = highs[j] if j < len(highs) else closes[j]
            l = lows[j] if j < len(lows) else closes[j]
            tp = (h + l + closes[j]) / 3.0
            vj = vols[j] if j < len(vols) and vols[j] > 0 else 1.0
            tp_sum += tp * vj
            v_sum += vj
        vwap = (tp_sum / v_sum) if v_sum > 0 else closes[i]

        if side == "BUY":
            rule_match = (
                closes[i] >= ema20[i]
                and ema20[i] >= ema50[i] * 0.995
                and closes[i] >= vwap * 0.995
                and rsi_series[i] >= 50.0
                and vol_r >= 1.1
            )
            ret_pct = ((closes[i + 1] - closes[i]) / closes[i]) * 100.0
        else:
            rule_match = (
                closes[i] <= ema20[i]
                and ema20[i] <= ema50[i] * 1.005
                and closes[i] <= vwap * 1.005
                and rsi_series[i] <= 52.0
                and vol_r >= 1.1
            )
            ret_pct = ((closes[i] - closes[i + 1]) / closes[i]) * 100.0

        if rule_match:
            cum_ret_pct += ret_pct
            if ret_pct > 0:
                wins += 1
            else:
                losses += 1

    tested = wins + losses
    win_rate = round((wins / tested) * 100.0, 1) if tested > 0 else 0.0
    latest_vol_avg = (sum(vols[-11:-1]) / 10.0) if len(vols) >= 11 and sum(vols[-11:-1]) > 0 else 1.0
    latest_vol = vols[-1] if vols else latest_vol_avg
    latest_vol_ratio = round(latest_vol / latest_vol_avg, 2) if latest_vol_avg > 0 else 1.0

    bb_up, bb_mid, bb_low = calc_bollinger(closes, 20, 2.0)
    rsi_now = rsi_series[-1]
    ltp = round(float(candles.get("ltp") or closes[-1]), 2)

    if side == "BUY":
        latest_ind_ok = (closes[-1] >= ema20[-1] * 0.995) and (rsi_now >= 48.0) and (closes[-1] <= bb_up * 1.04)
    else:
        latest_ind_ok = (closes[-1] <= ema20[-1] * 1.005) and (rsi_now <= 56.0) and (closes[-1] >= bb_low * 0.96)

    passed = bool(tested >= 3 and win_rate >= 60.0 and latest_vol_ratio >= 1.05 and latest_ind_ok)
    entry = round(ltp * (1.002 if side == "BUY" else 0.998), 2)
    target = round(entry * (1.022 if side == "BUY" else 0.978), 2)
    sl = round(entry * (0.988 if side == "BUY" else 1.012), 2)

    return {
        "symbol": symbol,
        "side": side,
        "ltp": ltp,
        "entry": entry,
        "target": target,
        "sl": sl,
        "trades_tested": tested,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "avg_return_pct": round(cum_ret_pct / tested, 2) if tested > 0 else 0.0,
        "vol_ratio": latest_vol_ratio,
        "rsi": rsi_now,
        "passed": passed,
    }


def scan_backtest_universe(symbols: List[str], side: str = "BUY") -> List[Dict]:
    results = []
    for sym in symbols:
        ticker = sym if (sym.startswith("^") or sym.endswith(".NS")) else f"{sym}.NS"
        try:
            candles = fetch_historical_candles(ticker, interval="1d", range_span="6mo")
            res = run_backtest_on_candles(sym, candles, side=side)
            results.append(res)
        except Exception as exc:
            results.append({
                "symbol": sym,
                "side": side,
                "trades_tested": 0,
                "win_rate": 0.0,
                "vol_ratio": 0.0,
                "rsi": 50.0,
                "passed": False,
                "error": str(exc),
            })
    results.sort(key=lambda r: (1 if r.get("passed") else 0, r.get("win_rate", 0.0)), reverse=True)
    return results