import os, sys, json, pathlib
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
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

class VectraHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/api/health", "/health"):
            return self._send_json({"status": "ok", "service": "VectraEdge"})
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
