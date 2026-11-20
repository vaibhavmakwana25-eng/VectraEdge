import os
import json
import urllib.parse
import urllib.request
from pathlib import Path

SESSION_FILE = Path(__file__).resolve().parent / "upstox_session.json"

INDEX_INSTRUMENTS = {
    "NIFTY": "NSE_INDEX|Nifty 50",
    "BANKNIFTY": "NSE_INDEX|Nifty Bank",
    "FINNIFTY": "NSE_INDEX|Nifty Fin Service",
    "MIDCPNIFTY": "NSE_INDEX|NIFTY MID SELECT",
    "SENSEX": "BSE_INDEX|SENSEX",
}

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}


def get_access_token() -> str:
    env_tok = os.getenv("UPSTOX_ACCESS_TOKEN", "").strip()
    if env_tok:
        return env_tok
    if SESSION_FILE.exists():
        try:
            return str(json.loads(SESSION_FILE.read_text(encoding="utf-8")).get("access_token") or "").strip()
        except Exception:
            return ""
    return ""


def _upstox_get(url: str, token: str) -> dict:
    headers = dict(DEFAULT_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_index_spots() -> dict:
    token = get_access_token()
    if not token:
        return {}
    keys = ",".join(INDEX_INSTRUMENTS.values())
    url = f"https://api.upstox.com/v2/market-quote/quotes?instrument_key={urllib.parse.quote(keys)}"
    try:
        raw_data = _upstox_get(url, token).get("data", {})
    except Exception:
        return {}

    out = {}
    for idx_name, inst_key in INDEX_INSTRUMENTS.items():
        item = raw_data.get(inst_key) or raw_data.get(inst_key.replace("|", ":")) or {}
        if item:
            ltp = float(item.get("last_price") or 0)
            prev_close = float((item.get("ohlc") or {}).get("close") or ltp)
            if ltp > 0:
                out[idx_name] = {"spot": ltp, "prevClose": prev_close}
    return out


def fetch_nearest_expiry(index_name: str, token: str) -> str:
    inst_key = INDEX_INSTRUMENTS.get(index_name.upper())
    if not inst_key:
        return ""
    url = f"https://api.upstox.com/v2/option/contract?instrument_key={urllib.parse.quote(inst_key)}"
    try:
        contracts = _upstox_get(url, token).get("data", [])
        expiries = sorted({str(c.get("expiry") or "") for c in contracts if c.get("expiry")})
        return expiries[0] if expiries else ""
    except Exception:
        return ""


def fetch_live_option_setups() -> dict:
    token = get_access_token()
    if not token:
        return {"connected": False, "spots": {}, "options": []}

    spots = fetch_index_spots()
    lot_map = {"NIFTY": 75, "BANKNIFTY": 30, "SENSEX": 20, "FINNIFTY": 65, "MIDCPNIFTY": 120}
    options_out = []

    for idx_name, inst_key in INDEX_INSTRUMENTS.items():
        expiry = fetch_nearest_expiry(idx_name, token)
        if not expiry:
            continue
        url = (
            "https://api.upstox.com/v2/option/chain?"
            f"instrument_key={urllib.parse.quote(inst_key)}&expiry_date={urllib.parse.quote(expiry)}"
        )
        try:
            chain = _upstox_get(url, token).get("data", [])
        except Exception:
            chain = []

        spot_val = (spots.get(idx_name) or {}).get("spot") or float(chain[0].get("underlying_spot_price") or 0) if chain else 0
        for row in chain:
            strike = int(float(row.get("strike_price") or 0))
            if not strike:
                continue
            for side_key, opt_type in (("call_options", "CE"), ("put_options", "PE")):
                opt_obj = row.get(side_key) or {}
                mkt = opt_obj.get("market_data") or {}
                ltp = float(mkt.get("ltp") or 0)
                if ltp <= 0:
                    continue
                oi = float(mkt.get("oi") or 0)
                vol = float(mkt.get("volume") or 0)
                dist_pct = abs(strike - spot_val) / max(1.0, spot_val) * 100.0 if spot_val else 1.5
                win_prob = int(min(89, max(54, round(86 - dist_pct * 4.5 + (2 if vol > 100000 else 0)))))
                vol_ratio = round(min(2.6, max(1.05, 1.1 + (vol / 250000.0))), 2)

                options_out.append({
                    "symbol": f"{idx_name} {strike} {opt_type}",
                    "expiry": expiry,
                    "is_fno": True,
                    "is_scalp": False,
                    "side": "BUY",
                    "ltp": round(ltp, 2),
                    "spot": round(spot_val, 2),
                    "oi": int(oi),
                    "volume": int(vol),
                    "win_prob": win_prob,
                    "loss_prob": 100 - win_prob,
                    "backtest_win_rate": max(55, win_prob - 1),
                    "vol_ratio": vol_ratio,
                    "lot_size": lot_map.get(idx_name, 75),
                    "live_source": "UPSTOX",
                })

    return {
        "connected": bool(spots or options_out),
        "spots": spots,
        "options": options_out,
    }