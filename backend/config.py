from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DRIVE_DATA_DIR = BASE_DIR / "google_drive_data"

HISTORICAL_DIR = DRIVE_DATA_DIR / "historical_2008_2026"
DAILY_UPDATES_DIR = DRIVE_DATA_DIR / "daily_updates"
BACKTEST_DIR = DRIVE_DATA_DIR / "backtest_results"
TRADES_BACKUP_DIR = DRIVE_DATA_DIR / "my_trades_backup"

# App & Signal Rules
APP_NAME = "VectraEdge"
EXECUTION_MODE = "SIGNAL_ONLY"          # App never places auto-trades; manual execution only
SCAN_INTERVAL_SECONDS = 60              # Scan every 60s during market hours
MIN_CONFIDENCE_SCORE = 0.75             # Strict threshold; emit NO signal if below this
REQUIRE_POSITIVE_NET_PROFIT = True      # Block signal if net profit after charges <= 0
HISTORY_START_YEAR = 2008
HISTORY_END_YEAR = 2026

# Zerodha Kite Connect placeholders (fill when ready)
ZERODHA_API_KEY = ""
ZERODHA_ACCESS_TOKEN = ""