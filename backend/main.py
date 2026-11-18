import os
﻿import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict

from agents.main_orchestrator import MainAgentOrchestrator
from config import APP_NAME, EXECUTION_MODE, SCAN_INTERVAL_SECONDS
from drive_sync import load_latest_trades_backup, save_trade_backup, verify_drive_folders
from zerodha_feed import get_market_candidates, is_zerodha_configured

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
ORCHESTRATOR = MainAgentOrchestrator()


class VectraEdgeHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, file_path: Path) -> None:
        if not file_path.exists():
            self._send_json({"error": "Frontend index.html not found"}, status=404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        if self.path == "/" or self.path == "/index.html":
            self._send_html(FRONTEND_DIR / "index.html")
            return

        if self.path == "/api/status":
            self._send_json({
                "app": APP_NAME,
                "mode": EXECUTION_MODE,
                "scan_interval_seconds": SCAN_INTERVAL_SECONDS,
                "zerodha_connected": is_zerodha_configured(),
                "drive_folders": verify_drive_folders(),
            })
            return

        if self.path == "/api/signals":
            candidates = get_market_candidates()
            signals = ORCHESTRATOR.scan_all(candidates)
            self._send_json({"signals": signals, "count": len(signals)})
            return

        if self.path == "/api/trades":
            self._send_json({"trades": load_latest_trades_backup()})
            return

        self._send_json({"error": "Not found"}, status=404)

    def do_POST(self) -> None:
        if self.path == "/api/trades/accept":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
            try:
                data = json.loads(raw)
            except Exception:
                self._send_json({"error": "Invalid JSON"}, status=400)
                return
            saved_path = save_trade_backup(data)
            self._send_json({"saved": True, "file": str(saved_path)})
            return

        self._send_json({"error": "Not found"}, status=404)


def run_server(port: int = 8000) -> None:
    verify_drive_folders()
    server = HTTPServer(("0.0.0.0", port), VectraEdgeHandler)
    print(f"{APP_NAME} running at http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_server()

