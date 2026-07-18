from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .resources import CONFIG_PATH, LEGACY_CONFIG_PATH, ensure_runtime_dirs


@dataclass(slots=True)
class AppConfig:
    device_name_patterns: list[str] = field(default_factory=lambda: ["Philips", "TAB4000"])
    tone_frequency_hz: float = 17_500.0
    frequencies_hz: list[float] = field(default_factory=lambda: [180.0, 420.0, 950.0, 2200.0])
    volume: float = 0.00035
    sample_rate_hz: int = 48_000
    block_size: int = 960
    watchdog_seconds: float = 2.0
    check_interval_seconds: float = 3.0
    keep_pc_awake: bool = True
    auto_start_with_windows: bool = True
    start_paused: bool = False
    log_level: str = "INFO"

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "AppConfig":
        patterns = raw.get("device_name_patterns", raw.get("device_keywords", ["Philips", "TAB4000"]))
        if isinstance(patterns, str):
            patterns = [patterns]
        elif not isinstance(patterns, list):
            patterns = ["Philips", "TAB4000"]

        normalized_patterns = [str(item).strip() for item in patterns if str(item).strip()]
        if not normalized_patterns:
            normalized_patterns = ["Philips", "TAB4000"]

        raw_frequencies = raw.get("frequencies_hz")
        if raw_frequencies is None and "tone_frequency_hz" in raw:
            raw_frequencies = [raw["tone_frequency_hz"]]
        elif raw_frequencies is None:
            raw_frequencies = [180.0, 420.0, 950.0, 2200.0]

        if isinstance(raw_frequencies, (int, float)):
            raw_frequencies = [float(raw_frequencies)]
        elif not isinstance(raw_frequencies, list):
            raw_frequencies = [180.0, 420.0, 950.0, 2200.0]

        normalized_frequencies = [float(value) for value in raw_frequencies if float(value) > 0.0]
        if not normalized_frequencies:
            normalized_frequencies = [180.0, 420.0, 950.0, 2200.0]

        return cls(
            device_name_patterns=normalized_patterns,
            tone_frequency_hz=float(raw.get("tone_frequency_hz", 17_500.0)),
            frequencies_hz=normalized_frequencies,
            volume=float(raw.get("volume", raw.get("base_amplitude", 0.00035))),
            sample_rate_hz=int(raw.get("sample_rate_hz", raw.get("sample_rate", 48_000))),
            block_size=max(0, int(raw.get("block_size", 960))),
            watchdog_seconds=max(0.5, float(raw.get("watchdog_seconds", 2.0))),
            check_interval_seconds=max(1.0, float(raw.get("check_interval_seconds", raw.get("device_scan_seconds", 3.0)))),
            keep_pc_awake=bool(raw.get("keep_pc_awake", True)),
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
            legacy_config = self._load_legacy_config()
            if legacy_config is not None:
                self.save(legacy_config)
                self._logger.info("Configuracao da V6 migrada de %s para %s", LEGACY_CONFIG_PATH, self._path)
                return legacy_config

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
        return self.load()

    def _load_legacy_config(self) -> AppConfig | None:
        if not LEGACY_CONFIG_PATH.exists():
            return None

        try:
            raw = json.loads(LEGACY_CONFIG_PATH.read_text(encoding="utf-8"))
            return AppConfig.from_dict(raw)
        except Exception:
            self._logger.exception("Falha ao migrar configuracao legada da V6.")
            return None

    def _update_mtime(self) -> None:
        if self._path.exists():
            self._last_mtime_ns = self._path.stat().st_mtime_ns
