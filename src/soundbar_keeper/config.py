from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .resources import CONFIG_PATH, ensure_runtime_dirs


@dataclass(slots=True)
class AppConfig:
    device_name_patterns: list[str] = field(default_factory=lambda: ["Philips TAB4000"])
    tone_frequency_hz: float = 17_500.0
    volume: float = 0.0005
    sample_rate_hz: int = 44_100
    check_interval_seconds: float = 3.0
    auto_start_with_windows: bool = True
    start_paused: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        patterns = raw.get("device_name_patterns", ["Philips TAB4000"])
        if isinstance(patterns, str):
            patterns = [patterns]
        elif not isinstance(patterns, list):
            patterns = ["Philips TAB4000"]

        normalized_patterns = [str(item).strip() for item in patterns if str(item).strip()]
        if not normalized_patterns:
            normalized_patterns = ["Philips TAB4000"]

        return cls(
            device_name_patterns=normalized_patterns,
            tone_frequency_hz=float(raw.get("tone_frequency_hz", 17_500.0)),
            volume=float(raw.get("volume", 0.0005)),
            sample_rate_hz=int(raw.get("sample_rate_hz", 44_100)),
            check_interval_seconds=max(1.0, float(raw.get("check_interval_seconds", 3.0))),
            auto_start_with_windows=bool(raw.get("auto_start_with_windows", True)),
            start_paused=bool(raw.get("start_paused", False)),
            log_level=str(raw.get("log_level", "INFO")).upper(),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ConfigManager:
    def __init__(self, logger: logging.Logger | None = None, path: Path = CONFIG_PATH) -> None:
        self._logger = logger or logging.getLogger(__name__)
        self._path = path
        self._last_mtime_ns: int | None = None

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> AppConfig:
        ensure_runtime_dirs()

        if not self._path.exists():
            config = AppConfig()
            self.save(config)
            self._logger.info("Arquivo de configuracao criado em %s", self._path)
            return config

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            config = AppConfig.from_dict(raw)
            self._update_mtime()
            return config
        except Exception:
            self._logger.exception("Falha ao carregar configuracao, usando padrao.")
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        ensure_runtime_dirs()
        payload = json.dumps(config.to_dict(), indent=2, ensure_ascii=False)
        self._path.write_text(f"{payload}\n", encoding="utf-8")
        self._update_mtime()

    def reload_if_changed(self) -> AppConfig | None:
        if not self._path.exists():
            return None

        current_mtime_ns = self._path.stat().st_mtime_ns
        if self._last_mtime_ns is None:
            self._last_mtime_ns = current_mtime_ns
            return None

        if current_mtime_ns == self._last_mtime_ns:
            return None

        self._logger.info("Alteracao detectada no arquivo de configuracao.")
        config = self.load()
        return config

    def _update_mtime(self) -> None:
        if self._path.exists():
            self._last_mtime_ns = self._path.stat().st_mtime_ns
