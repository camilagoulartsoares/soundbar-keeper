from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "Soundbar Keeper"
APP_SLUG = "soundbar_keeper"
RUNTIME_DIR_NAME = "SoundbarKeeper"
LEGACY_RUNTIME_DIR_NAME = "SoundbarKeeperV6"

PACKAGE_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PACKAGE_ROOT.parent
PROJECT_ROOT = SRC_ROOT.parent

ASSETS_DIR = PROJECT_ROOT / "assets"
SCREENSHOTS_DIR = ASSETS_DIR / "screenshots"
ICON_PATH = ASSETS_DIR / "icon.ico"

LOCAL_APPDATA_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
RUNTIME_DIR = LOCAL_APPDATA_ROOT / RUNTIME_DIR_NAME
LEGACY_RUNTIME_DIR = LOCAL_APPDATA_ROOT / LEGACY_RUNTIME_DIR_NAME
LOGS_DIR = RUNTIME_DIR / "logs"
LOG_FILE_PATH = LOGS_DIR / "soundbar-keeper.log"
CONFIG_PATH = RUNTIME_DIR / "config.json"
LEGACY_CONFIG_PATH = LEGACY_RUNTIME_DIR / "config.json"


def ensure_runtime_dirs() -> None:
    """Create runtime folders if they don't exist yet."""
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
