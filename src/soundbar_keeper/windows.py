from __future__ import annotations

import ctypes
import os
import sys
from pathlib import Path

from .resources import PROJECT_ROOT, SRC_ROOT

STARTUP_SCRIPT_NAME = "Soundbar Keeper.cmd"
SINGLE_INSTANCE_MUTEX_NAME = "Global\\SoundbarKeeper_SingleInstance"
ERROR_ALREADY_EXISTS = 183
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001

kernel32 = ctypes.windll.kernel32


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
            f'"{python_executable}" -m soundbar_keeper\n'
        )


class SingleInstanceGuard:
    def __init__(self, mutex_name: str = SINGLE_INSTANCE_MUTEX_NAME) -> None:
        self._mutex_name = mutex_name
        self._handle: int | None = None

    def acquire(self) -> bool:
        handle = kernel32.CreateMutexW(None, False, self._mutex_name)
        if not handle:
            raise OSError("Nao foi possivel criar o mutex da aplicacao.")

        self._handle = int(handle)
        return kernel32.GetLastError() != ERROR_ALREADY_EXISTS

    def release(self) -> None:
        if self._handle is None:
            return

        kernel32.CloseHandle(self._handle)
        self._handle = None


class WindowsPowerManager:
    def refresh(self, keep_awake: bool) -> None:
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED if keep_awake else ES_CONTINUOUS
        kernel32.SetThreadExecutionState(flags)


def open_path(path: Path) -> None:
    os.startfile(str(path))


def _resolve_pythonw_executable() -> Path:
    executable = Path(sys.executable)
    pythonw_candidate = executable.with_name("pythonw.exe")
    if pythonw_candidate.exists():
        return pythonw_candidate
    return executable
