import os, sys, json, pathlib
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

BASE_DIR = pathlib.Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
FRONTEND_DIR = ROOT_DIR / "frontend"
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from agents.main_orchestrator import MainAgentOrchestrator
from drive_sync import verify_drive_folders, save_trade_backup, load_latest_trades_backup
from zerodha_feed import get_market_candidates, is_zerodha_configured

orchestrator = MainAgentOrchestrator()

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
            save_trade_backup(trade)
            trades = load_latest_trades_backup()
            return self._send_json({"ok": True, "trade": trade, "trades": trades})
        self._send_json({"error": "Not found"}, 404)

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/api/status", "/api/health", "/health"):
            folders = verify_drive_folders()
            drive_ready = all(folders.values()) if folders else False
            zerodha_live = is_zerodha_configured()
            return self._send_json({
                "ok": True,
                "online": True,
                "status": "Online",
                "drive_sync": "Connected (Ready)" if drive_ready else "Check Folders",
                "feed": "Zerodha Live" if zerodha_live else "Paper/Sample Feed",
                "drive_folders": folders, "zerodha_connected": zerodha_live
            })
        if path in ("/api/signals", "/signals"):
            raw = get_market_candidates()
            signals = orchestrator.scan_all(raw)
            if not signals:
                signals = raw
            return self._send_json({"ok": True, "signals": signals})
        if path == "/api/trades":
            trades = load_latest_trades_backup()
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
    verify_drive_folders()
    port = int(os.environ.get("PORT", 8000))
    server = ThreadingHTTPServer(("0.0.0.0", port), VectraHandler)
    print(f"VectraEdge live on 0.0.0.0:{port}", flush=True)
    server.serve_forever()
