import os, sys, json, pathlib
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
TRADES_FILE = ROOT_DIR / "google_drive_data" / "trades.json"
TRADES_FILE.parent.mkdir(parents=True, exist_ok=True)
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.main_orchestrator import MainAgentOrchestrator

try:
    from zerodha_feed import fetch_candidates
except Exception:
    fetch_candidates = None

try:
    from drive_sync import sync_signals
except Exception:
    sync_signals = None

orchestrator = MainAgentOrchestrator()

SAMPLE_CANDIDATES = [
    {"symbol": "NIFTY 24500 CE", "segment": "NFO", "ltp": 145.0, "entry": 145.0, "target": 185.0, "min_target": 165.0, "sl": 125.0, "min_sl": 130.0, "lot_size": 75, "side": "BUY", "is_fno": True},
    {"symbol": "BANKNIFTY 52000 PE", "segment": "NFO", "ltp": 210.0, "entry": 210.0, "target": 275.0, "min_target": 240.0, "sl": 180.0, "min_sl": 190.0, "lot_size": 30, "side": "BUY", "is_fno": True}
]

def load_trades():
    if TRADES_FILE.is_file():
        try:
            return json.loads(TRADES_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []

def save_trades(trades):
    TRADES_FILE.write_text(json.dumps(trades, indent=2), encoding="utf-8")

class VectraHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({"ok": True})

    def do_POST(self):
        path = self.path.split("?")[0]
        if path == "/api/trades/accept":
            length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(length).decode("utf-8") if length else "{}"
            try:
                trade = json.loads(raw_body)
            except Exception:
                trade = {}
            trade["logged_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            trades = load_trades()
            trades.insert(0, trade)
            save_trades(trades)
            return self._send_json({"ok": True, "trade": trade, "trades": trades})
        self._send_json({"error": "Not found"}, 404)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/api/status", "/api/health", "/health"):
            return self._send_json({"ok": True, "online": True, "status": "Online", "feed": "Live", "service": "VectraEdge"})
        if path in ("/api/signals", "/signals"):
            raw = fetch_candidates() if callable(fetch_candidates) else SAMPLE_CANDIDATES
            signals = orchestrator.scan_all(raw or SAMPLE_CANDIDATES)
            if not signals:
                signals = raw or SAMPLE_CANDIDATES
            if callable(sync_signals):
                try:
                    sync_signals(signals)
                except Exception:
                    pass
            return self._send_json({"ok": True, "signals": signals})
        if path == "/api/trades":
            trades = load_trades()
            return self._send_json({"ok": True, "trades": trades})

        rel = "index.html" if path == "/" else path.lstrip("/")
        target = (FRONTEND_DIR / rel).resolve()
        if str(target).startswith(str(FRONTEND_DIR.resolve())) and target.is_file():
            ct = "text/html; charset=utf-8" if target.suffix == ".html" else (
                 "application/manifest+json" if target.suffix == ".json" else (
                 "application/javascript" if target.suffix == ".js" else (
                 "image/png" if target.suffix == ".png" else "application/octet-stream")))
            data = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ct)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        index_file = FRONTEND_DIR / "index.html"
        if index_file.is_file():
            data = index_file.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._send_json({"error": "Not found"}, 404)

    def log_message(self, format, *args):
        print(f"[VectraEdge] {args[0]}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(("0.0.0.0", port), VectraHandler)
    print(f"VectraEdge live on 0.0.0.0:{port}", flush=True)
    server.serve_forever()
