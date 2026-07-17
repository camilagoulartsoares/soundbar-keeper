from __future__ import annotations

import os
import sys
from pathlib import Path

from .resources import PROJECT_ROOT, SRC_ROOT

STARTUP_SCRIPT_NAME = "Soundbar Keeper.cmd"


class WindowsStartupManager:
    def __init__(self, project_root: Path = PROJECT_ROOT, src_root: Path = SRC_ROOT) -> None:
        self._project_root = project_root
        self._src_root = src_root

    @property
    def startup_script_path(self) -> Path:
        appdata = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        startup_dir = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return startup_dir / STARTUP_SCRIPT_NAME

    def install(self) -> Path:
        target = self.startup_script_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self._build_script(), encoding="utf-8")
        return target

    def uninstall(self) -> None:
        target = self.startup_script_path
        if target.exists():
            target.unlink()

    def is_enabled(self) -> bool:
        return self.startup_script_path.exists()

    def _build_script(self) -> str:
        python_executable = _resolve_pythonw_executable()
        return (
            "@echo off\n"
            f'cd /d "{self._project_root}"\n'
            f'set "PYTHONPATH={self._src_root};%PYTHONPATH%"\n'
            f'"{python_executable}" -m soundbar_keeper.main\n'
        )


def open_path(path: Path) -> None:
    os.startfile(str(path))


def _resolve_pythonw_executable() -> Path:
    executable = Path(sys.executable)
    pythonw_candidate = executable.with_name("pythonw.exe")
    if pythonw_candidate.exists():
        return pythonw_candidate
    return executable
