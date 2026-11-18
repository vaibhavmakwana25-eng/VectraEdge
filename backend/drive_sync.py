import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config import (
    BACKTEST_DIR,
    DAILY_UPDATES_DIR,
    DRIVE_DATA_DIR,
    HISTORICAL_DIR,
    TRADES_BACKUP_DIR,
)


def verify_drive_folders() -> Dict[str, bool]:
    """Checks that all required Google Drive sync folders exist and are ready."""
    folders = {
        "drive_root": DRIVE_DATA_DIR,
        "historical_2008_2026": HISTORICAL_DIR,
        "daily_updates": DAILY_UPDATES_DIR,
        "backtest_results": BACKTEST_DIR,
        "my_trades_backup": TRADES_BACKUP_DIR,
    }
    status: Dict[str, bool] = {}
    for name, path in folders.items():
        path.mkdir(parents=True, exist_ok=True)
        status[name] = path.exists() and path.is_dir()
    return status


def save_trade_backup(trade_record: Dict[str, Any]) -> Path:
    """Saves an accepted trade or daily summary backup into my_trades_backup."""
    TRADES_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    file_path = TRADES_BACKUP_DIR / f"trades_backup_{stamp}.json"

    existing: list = []
    if file_path.exists():
        try:
            content = file_path.read_text(encoding="utf-8").strip()
            if content:
                existing = json.loads(content)
                if not isinstance(existing, list):
                    existing = [existing]
        except Exception:
            existing = []

    record_with_time = {
        **trade_record,
        "saved_at": datetime.now().isoformat(),
    }
    existing.append(record_with_time)
    file_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return file_path


def load_latest_trades_backup() -> list:
    """Loads today's saved trades backup safely without crashing on empty/missing files."""
    TRADES_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d")
    file_path = TRADES_BACKUP_DIR / f"trades_backup_{stamp}.json"
    if not file_path.exists():
        return []
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []