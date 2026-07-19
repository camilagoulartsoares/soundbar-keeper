import argparse
import ctypes
import json
import logging
from logging.handlers import RotatingFileHandler
import math
import msvcrt
import os
from pathlib import Path
import random
import socket
import subprocess
import sys
import threading
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Deque, Optional

import comtypes
import numpy as np
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw
from pycaw.pycaw import AudioUtilities, IAudioMeterInformation


APP_NAME = "PhilipsTAB4000KeepAliveV9"
APP_BASE_DIR = os.environ.get("PHILIPS_KEEPALIVE_BASEDIR") or os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
APP_DIR = Path(APP_BASE_DIR) / APP_NAME
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = APP_DIR / "config.json"
LOG_DIR = APP_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "keepalive.log"
LOCK_FILE = APP_DIR / "instance.lock"
STATUS_FILE = APP_DIR / "tray_status.json"
TRAY_COMMAND_FILE = APP_DIR / "tray_command.json"
TASK_NAME = APP_NAME
MUTEX_NAME = os.environ.get("PHILIPS_KEEPALIVE_MUTEX_NAME", f"Global\\{APP_NAME}Mutex")
INSTANCE_PORT = int(os.environ.get("PHILIPS_KEEPALIVE_INSTANCE_PORT", "45409"))

LEGACY_TASKS = [
    "PhilipsSoundbarKeepAliveV6",
    "PhilipsSoundbarKeepAliveV7",
    "PhilipsSoundbarKeepAliveV8",
    "SoundbarKeepAliveV6",
    "SoundbarKeepAliveV7",
    "SoundbarKeepAliveV8",
    "PhilipsTAB4000KeepAliveV6",
    "PhilipsTAB4000KeepAliveV7",
    "PhilipsTAB4000KeepAliveV8",
]
LEGACY_PROCESS_PATTERNS = [
    "soundbar_keeper_v6",
    "soundbar_keeper_v7",
    "soundbar_keeper_v8",
    "PhilipsTAB4000KeepAliveV6",
    "PhilipsTAB4000KeepAliveV7",
    "PhilipsTAB4000KeepAliveV8",
]
LEGACY_STARTUP_FILES = [
    "PhilipsSoundbarKeepAliveV6.lnk",
    "PhilipsSoundbarKeepAliveV7.lnk",
    "PhilipsSoundbarKeepAliveV8.lnk",
    "SoundbarKeepAliveV6.lnk",
    "SoundbarKeepAliveV7.lnk",
    "SoundbarKeepAliveV8.lnk",
    "PhilipsTAB4000KeepAliveV6.lnk",
    "PhilipsTAB4000KeepAliveV7.lnk",
    "PhilipsTAB4000KeepAliveV8.lnk",
]

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ERROR_ALREADY_EXISTS = 183

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)


DEFAULT_CONFIG = {
    "version": 9,
    "device": {
        "keywords": ["Philips", "TAB4000"],
        "prefer_wasapi": True,
        "sample_rate": 48000,
        "channels": 2,
        "block_size": 480,
        "latency": "high",
    },
    "audio": {
        "shared_mode": True,
        "dtype": "float32",
        "keep_stream_open": True,
    },
    "pulse": {
        "duration_ms_min": 3.0,
        "duration_ms_max": 6.0,
        "interval_seconds_min": 3.0,
        "interval_seconds_max": 5.0,
        "frequency_hz_min": 18000.0,
        "frequency_hz_max": 19200.0,
        "envelope": "blackman",
    },
    "adaptive_mode": {
        "enabled": True,
        "resume_after_silence_seconds": 3.0,
    },
    "random_frequency": True,
    "amplitude_dbfs": {
        "minimum": -78.0,
        "current": -72.0,
        "maximum": -54.0,
        "steps": [-78.0, -72.0, -66.0, -60.0, -54.0],
    },
    "audio_detection": {
        "enabled": False,
        "activate_threshold": 0.0015,
        "release_threshold": 0.0007,
        "attack_seconds": 0.15,
        "release_seconds": 3.0,
        "poll_interval_seconds": 0.05,
        "ignore_pulse_window_seconds": 0.2,
    },
    "watchdog": {
        "poll_interval_seconds": 0.5,
        "callback_stall_seconds": 6.0,
        "resume_gap_seconds": 15.0,
        "backoff_seconds": [1, 2, 4, 8, 15],
    },
    "startup": {
        "ensure_task": True,
        "task_delay_seconds": 10,
    },
    "tray": {
        "enabled": True,
        "show_notifications": False,
    },
    "debug": {
        "log_device_scan": True,
        "log_audio_detector": False,
    },
    "logging": {
        "max_bytes": 262144,
        "backup_count": 3,
    },
    "limitations": {
        "physical_standby_detection": (
            "The Windows audio stack does not expose a reliable standby telemetry signal for this soundbar. "
            "The app cannot prove whether the speaker is physically awake."
        )
    },
}


LOGGER = logging.getLogger(APP_NAME)
LOGGER.setLevel(logging.INFO)


def dbfs_to_linear(dbfs: float) -> float:
    return float(10.0 ** (dbfs / 20.0))


def deep_merge(base: dict, override: dict) -> dict:
    result = {}
    for key, value in base.items():
        if isinstance(value, dict):
            nested_override = override.get(key, {}) if isinstance(override.get(key), dict) else {}
            result[key] = deep_merge(value, nested_override)
        else:
            result[key] = override.get(key, value)
    for key, value in override.items():
        if key not in result:
            result[key] = value
    return result


def configure_logging(config: dict) -> None:
    if LOGGER.handlers:
        return
    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=int(config["logging"]["max_bytes"]),
        backupCount=int(config["logging"]["backup_count"]),
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        return json.loads(json.dumps(DEFAULT_CONFIG))
    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        raw = {}
    merged = deep_merge(DEFAULT_CONFIG, raw)
    CONFIG_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
    return merged


def atomic_write_json(path: Path, payload: dict) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


def load_json_file(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


@dataclass
class PulseEvent:
    start_sample: int
    samples: np.ndarray

    @property
    def end_sample(self) -> int:
        return self.start_sample + int(self.samples.shape[0])


class AppState(str, Enum):
    WAITING_FOR_DEVICE = "WAITING_FOR_DEVICE"
    OPENING_STREAM = "OPENING_STREAM"
    RUNNING = "RUNNING"
    REAL_AUDIO_ACTIVE = "REAL_AUDIO_ACTIVE"
    RECOVERING = "RECOVERING"
    STOPPING = "STOPPING"


class PulsePlanner:
    def __init__(self, config: dict):
        self.pulse_cfg = config["pulse"]
        self.sample_rate = int(config["device"]["sample_rate"])
        self.channels = int(config["device"]["channels"])
        self.amplitude = dbfs_to_linear(float(config["amplitude_dbfs"]["current"]))
        self.events: Deque[PulseEvent] = deque()
        self.lock = threading.Lock()
        self.position = 0
        self.planned_until = 0
        self.next_pulse_sample = self.sample_rate
        self.horizon_samples = int(self.sample_rate * 12)
        self.real_audio_active = False
        self.stop_event = threading.Event()
        self.last_callback_time = time.monotonic()
        self.last_callback_sample = 0
        self.last_pulse_monotonic = 0.0
        self.thread = threading.Thread(target=self._planner_loop, name="PulsePlanner", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=2)

    def reconfigure_stream(self, sample_rate: int, channels: int, amplitude_dbfs: float) -> None:
        with self.lock:
            self.sample_rate = int(sample_rate)
            self.channels = int(channels)
            self.amplitude = dbfs_to_linear(float(amplitude_dbfs))
            self.position = 0
            self.planned_until = 0
            self.next_pulse_sample = self.sample_rate
            self.horizon_samples = int(self.sample_rate * 12)
            self.last_callback_sample = 0
            self.events.clear()

    def update_position(self, position: int) -> None:
        with self.lock:
            self.position = position
            self.last_callback_sample = position
            self.last_callback_time = time.monotonic()

    def set_real_audio_active(self, active: bool) -> None:
        with self.lock:
            self.real_audio_active = active
            if active:
                self.events.clear()

    def get_last_callback_snapshot(self) -> tuple[float, int]:
        with self.lock:
            return self.last_callback_time, self.last_callback_sample

    def pulse_ignore_window_active(self, ignore_seconds: float) -> bool:
        return (time.monotonic() - self.last_pulse_monotonic) <= ignore_seconds

    def mix_into(self, outdata: np.ndarray, frames: int, block_start: int) -> None:
        block_end = block_start + frames
        used = False
        with self.lock:
            while self.events and self.events[0].end_sample <= block_start:
                self.events.popleft()
            for event in list(self.events):
                if event.start_sample >= block_end:
                    break
                overlap_start = max(block_start, event.start_sample)
                overlap_end = min(block_end, event.end_sample)
                if overlap_end <= overlap_start:
                    continue
                dst_start = overlap_start - block_start
                src_start = overlap_start - event.start_sample
                src_end = src_start + (overlap_end - overlap_start)
                outdata[dst_start : dst_start + (overlap_end - overlap_start)] += event.samples[src_start:src_end]
                used = True
            if used:
                self.last_pulse_monotonic = time.monotonic()

    def _planner_loop(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                current = self.position
                paused = self.real_audio_active
                while self.events and self.events[0].end_sample <= current:
                    self.events.popleft()
                if paused:
                    self.planned_until = current
                    self.next_pulse_sample = max(self.next_pulse_sample, current + int(self.sample_rate * 3))
                else:
                    if self.next_pulse_sample < current + self.sample_rate:
                        self.next_pulse_sample = current + self.sample_rate
                    while self.planned_until < current + self.horizon_samples:
                        event = self._build_event(self.next_pulse_sample)
                        self.events.append(event)
                        self.planned_until = event.end_sample
                        gap_seconds = random.uniform(
                            float(self.pulse_cfg["interval_seconds_min"]),
                            float(self.pulse_cfg["interval_seconds_max"]),
                        )
                        self.next_pulse_sample = event.end_sample + int(gap_seconds * self.sample_rate)
            self.stop_event.wait(0.1)

    def _build_event(self, start_sample: int) -> PulseEvent:
        duration_ms = random.uniform(
            float(self.pulse_cfg["duration_ms_min"]),
            float(self.pulse_cfg["duration_ms_max"]),
        )
        sample_count = max(8, int(self.sample_rate * duration_ms / 1000.0))
        max_frequency = min(
            float(self.pulse_cfg["frequency_hz_max"]),
            max(1000.0, (self.sample_rate / 2.0) - 200.0),
        )
        min_frequency = min(float(self.pulse_cfg["frequency_hz_min"]), max_frequency)
        frequency = random.uniform(min_frequency, max_frequency)
        phase0 = random.uniform(0.0, 2.0 * math.pi)
        t = np.arange(sample_count, dtype=np.float32) / np.float32(self.sample_rate)
        if self.pulse_cfg.get("envelope", "blackman").lower() == "hann":
            envelope = np.hanning(sample_count).astype(np.float32)
        else:
            envelope = np.blackman(sample_count).astype(np.float32)
        waveform = np.sin((2.0 * math.pi * frequency * t) + phase0).astype(np.float32)
        mono = (waveform * envelope * np.float32(self.amplitude)).astype(np.float32)
        stereo = np.repeat(mono[:, None], self.channels, axis=1)
        return PulseEvent(start_sample=start_sample, samples=stereo)


class OutputAudioMonitor:
    def __init__(self, config: dict, pulse_planner: PulsePlanner):
        self.config = config["audio_detection"]
        self.pulse_planner = pulse_planner
        self.active = False
        self.real_audio_started_at: Optional[float] = None
        self.silence_started_at: Optional[float] = None
        self.last_peak = 0.0
        self.last_error_log = 0.0

    def poll(self) -> bool:
        if not self.config["enabled"]:
            return False
        peak = self._read_peak()
        self.last_peak = peak
        now = time.monotonic()
        if self.pulse_planner.pulse_ignore_window_active(float(self.config["ignore_pulse_window_seconds"])):
            return self.active

        activate_threshold = float(self.config["activate_threshold"])
        release_threshold = float(self.config["release_threshold"])

        if peak >= activate_threshold:
            self.silence_started_at = None
            if self.real_audio_started_at is None:
                self.real_audio_started_at = now
            if not self.active and (now - self.real_audio_started_at) >= float(self.config["attack_seconds"]):
                self.active = True
                LOGGER.info("Real audio detected on the Windows endpoint. Pulses paused.")
        elif peak <= release_threshold:
            self.real_audio_started_at = None
            if self.silence_started_at is None:
                self.silence_started_at = now
            if self.active and (now - self.silence_started_at) >= float(self.config["release_seconds"]):
                self.active = False
                LOGGER.info("Continuous silence detected for %.2f seconds. Pulses resumed.", float(self.config["release_seconds"]))
        return self.active

    def _read_peak(self) -> float:
        try:
            speakers = AudioUtilities.GetSpeakers()
            interface = speakers._dev.Activate(IAudioMeterInformation._iid_, comtypes.CLSCTX_ALL, None)
            meter = ctypes.cast(interface, ctypes.POINTER(IAudioMeterInformation))
            return float(meter.GetPeakValue())
        except Exception as exc:
            now = time.monotonic()
            if now - self.last_error_log > 10:
                LOGGER.warning("Could not read output peak meter via Core Audio: %s", exc)
                self.last_error_log = now
            return 0.0


class TrayController:
    def __init__(self):
        self.icon: Optional[pystray.Icon] = None
        self.icon_image = self._icon_image()
        self.lock = threading.Lock()
        self.available = False
        self.failed = False
        self.running = threading.Event()
        self.running.set()
        self.status = {
            "status_line": "Inicializando",
            "current_device_label": "nenhum",
        }
        self.refresh_thread = threading.Thread(target=self._refresh_loop, name="TrayRefresh", daemon=True)

    def run(self) -> int:
        try:
            self._load_status()
            self.icon = pystray.Icon(APP_NAME, self.icon_image, self._tooltip_text(), self._menu())
            self.available = True
            self.refresh_thread.start()
            self.icon.run()
            return 0
        except Exception as exc:
            self._disable_tray("Tray run failed", exc)
            return 1
        finally:
            self.running.clear()
            self.available = False

    def _refresh_loop(self) -> None:
        while self.running.is_set():
            time.sleep(1.0)
            self.refresh()

    def refresh(self) -> None:
        with self.lock:
            if not self.available or self.icon is None:
                return
            try:
                self._load_status()
                self.icon.title = self._tooltip_text()
                self.icon.update_menu()
            except Exception as exc:
                self._disable_tray("Tray refresh failed", exc)

    def stop(self) -> None:
        self.running.clear()
        with self.lock:
            if self.icon is None:
                return
            try:
                self.icon.stop()
            except Exception as exc:
                self._disable_tray("Tray stop failed", exc)

    def _disable_tray(self, message: str, exc: Exception) -> None:
        self.failed = True
        self.available = False
        self.running.clear()
        LOGGER.exception("%s. Continuing without tray support.", message, exc_info=exc)
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass
            self.icon = None

    def _load_status(self) -> None:
        payload = load_json_file(STATUS_FILE)
        if payload:
            self.status.update(payload)

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda item: self.status["status_line"], self._noop, enabled=False),
            pystray.MenuItem(lambda item: f"Dispositivo: {self.status['current_device_label']}", self._noop, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Abrir pasta de logs", self._open_logs),
            pystray.MenuItem("Reiniciar audio", self._restart_audio),
            pystray.MenuItem("Sair", self._quit),
        )

    def _icon_image(self) -> Image.Image:
        active = self.app.state in {AppState.RUNNING, AppState.REAL_AUDIO_ACTIVE}
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        fill = (28, 126, 96, 255) if active else (145, 82, 32, 255)
        draw.rounded_rectangle((7, 17, 57, 47), radius=10, fill=fill)
        draw.arc((17, 22, 47, 42), 200, 340, fill=(255, 255, 255, 255), width=3)
        draw.rectangle((24, 18, 40, 22), fill=(255, 255, 255, 200))
        return image

    def _tooltip_text(self) -> str:
        return f"{APP_NAME} | {self.status['status_line']}"

    def _noop(self, icon, item) -> None:
        return None

    def _open_logs(self, icon, item) -> None:
        try:
            os.startfile(str(LOG_DIR))
        except Exception as exc:
            LOGGER.exception("Tray action failed while opening logs.", exc_info=exc)

    def _restart_audio(self, icon, item) -> None:
        try:
            atomic_write_json(TRAY_COMMAND_FILE, {"command": "restart", "timestamp": time.time()})
        except Exception as exc:
            LOGGER.exception("Tray action failed while requesting audio restart.", exc_info=exc)

    def _quit(self, icon, item) -> None:
        try:
            atomic_write_json(TRAY_COMMAND_FILE, {"command": "quit", "timestamp": time.time()})
            self.stop()
        except Exception as exc:
            LOGGER.exception("Tray action failed while stopping the application.", exc_info=exc)


class KeepAliveApp:
    def __init__(self, config: dict, args: argparse.Namespace):
        self.config = config
        self.args = args
        self.state = AppState.WAITING_FOR_DEVICE
        self.status_line = "Inicializando"
        self.current_device_label = "nenhum"
        self.running = threading.Event()
        self.running.set()
        self.restart_requested = threading.Event()
        self.stream_lock = threading.Lock()
        self.stream: Optional[sd.OutputStream] = None
        self.stream_device_id: Optional[int] = None
        self.backoff_index = 0
        self.last_supervisor_tick = time.monotonic()
        self.tray_enabled = bool(self.config["tray"]["enabled"]) and os.environ.get("PHILIPS_KEEPALIVE_ENABLE_TRAY") == "1"
        self.audio_detection_enabled = bool(self.config["audio_detection"]["enabled"]) and os.environ.get("PHILIPS_KEEPALIVE_ENABLE_AUDIO_DETECTION") == "1"
        self.pulse_planner = PulsePlanner(config)
        self.audio_monitor = OutputAudioMonitor(config, self.pulse_planner)
        self.tray_process: Optional[subprocess.Popen] = None
        self.tray_warning_logged = False
        self.supervisor_thread = threading.Thread(target=self._supervisor_loop, name="Supervisor", daemon=True)
        self.monitor_thread = threading.Thread(target=self._audio_monitor_loop, name="AudioMonitor", daemon=True)

    def start(self) -> int:
        LOGGER.info("Starting %s", APP_NAME)
        LOGGER.info("Limitation: %s", self.config["limitations"]["physical_standby_detection"])
        self.cleanup_legacy_versions()
        if self.config["startup"]["ensure_task"] and not self.args.skip_startup_task:
            self.ensure_startup_task()
        self.pulse_planner.start()
        self.supervisor_thread.start()
        if bool(self.config["audio_detection"]["enabled"]) and not self.audio_detection_enabled:
            LOGGER.warning("Audio detection disabled by safety gate. Set PHILIPS_KEEPALIVE_ENABLE_AUDIO_DETECTION=1 to enable the optional Core Audio monitor.")
        if self.audio_detection_enabled:
            self.monitor_thread.start()
        self._publish_status()
        if self.args.no_tray:
            deadline = time.monotonic() + float(self.args.debug_seconds or 15)
            while self.running.is_set() and time.monotonic() < deadline:
                time.sleep(0.2)
            self.stop()
            return 0
        if bool(self.config["tray"]["enabled"]) and not self.tray_enabled:
            LOGGER.warning("Tray launch disabled by safety gate. Set PHILIPS_KEEPALIVE_ENABLE_TRAY=1 to enable the optional tray helper.")
        if self.tray_enabled:
            self._start_tray_process()
        while self.running.is_set():
            self._publish_status()
            self._check_tray_process()
            time.sleep(0.2)
        return 0

    def stop(self) -> None:
        if not self.running.is_set():
            return
        self.state = AppState.STOPPING
        self.status_line = "Encerrando"
        self.running.clear()
        self._publish_status()
        self._close_stream()
        self.pulse_planner.stop()
        self._stop_tray_process()
        kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        LOGGER.info("Application stopped.")

    def request_restart(self) -> None:
        LOGGER.info("Audio restart requested by user.")
        self.restart_requested.set()

    def cleanup_legacy_versions(self) -> None:
        startup_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        for pattern in LEGACY_PROCESS_PATTERNS:
            self._run_command(["taskkill", "/F", "/IM", f"{pattern}.exe"], ok_codes={0, 128}, log_errors=False)
        for task_name in LEGACY_TASKS:
            self._run_command(["schtasks", "/End", "/TN", task_name], ok_codes={0, 1}, log_errors=False)
            self._run_command(["schtasks", "/Delete", "/TN", task_name, "/F"], ok_codes={0, 1}, log_errors=False)
        for filename in LEGACY_STARTUP_FILES:
            shortcut = startup_dir / filename
            if shortcut.exists():
                shortcut.unlink(missing_ok=True)
                LOGGER.info("Removed legacy startup shortcut: %s", shortcut)

    def ensure_startup_task(self) -> None:
        if self._scheduled_task_exists():
            LOGGER.info("Scheduled task already present: %s", TASK_NAME)
            return
        command = self._startup_command()
        delay_seconds = int(self.config["startup"]["task_delay_seconds"])
        delay = f"{delay_seconds // 60:04d}:{delay_seconds % 60:02d}"
        created = self._run_command(
            [
                "schtasks",
                "/Create",
                "/TN",
                TASK_NAME,
                "/SC",
                "ONLOGON",
                "/DELAY",
                delay,
                "/RL",
                "LIMITED",
                "/TR",
                command,
                "/F",
            ],
            ok_codes={0},
        )
        if created:
            LOGGER.info("Scheduled task ensured: %s", TASK_NAME)
        else:
            LOGGER.warning("Could not create scheduled task %s. The app can still run manually.", TASK_NAME)

    def remove_startup_task(self) -> None:
        self._run_command(["schtasks", "/Delete", "/TN", TASK_NAME, "/F"], ok_codes={0, 1}, log_errors=False)

    def _scheduled_task_exists(self) -> bool:
        return self._run_command(["schtasks", "/Query", "/TN", TASK_NAME], ok_codes={0}, log_errors=False)

    def _startup_command(self) -> str:
        if getattr(sys, "frozen", False):
            return f'"{Path(sys.executable).resolve()}"'
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        return f'"{pythonw}" "{Path(__file__).resolve()}"'

    def _audio_monitor_loop(self) -> None:
        comtypes.CoInitialize()
        poll_interval = float(self.config["audio_detection"]["poll_interval_seconds"])
        try:
            while self.running.is_set():
                active = self.audio_monitor.poll()
                self.pulse_planner.set_real_audio_active(active)
                if active and self.state == AppState.RUNNING:
                    self.state = AppState.REAL_AUDIO_ACTIVE
                    self.status_line = "Audio real detectado; pulsos pausados"
                elif not active and self.state == AppState.REAL_AUDIO_ACTIVE:
                    self.state = AppState.RUNNING
                    if self.current_device_label != "nenhum":
                        self.status_line = f"Ativo em {self.current_device_label}"
                if self.config["debug"]["log_audio_detector"]:
                    LOGGER.info("Audio peak=%.6f active=%s", self.audio_monitor.last_peak, active)
                self._publish_status()
                time.sleep(poll_interval)
        finally:
            comtypes.CoUninitialize()

    def _supervisor_loop(self) -> None:
        comtypes.CoInitialize()
        poll_interval = float(self.config["watchdog"]["poll_interval_seconds"])
        resume_gap = float(self.config["watchdog"]["resume_gap_seconds"])
        try:
            while self.running.is_set():
                try:
                    kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
                    now = time.monotonic()
                    if (now - self.last_supervisor_tick) > resume_gap:
                        LOGGER.info("Large monotonic gap detected after suspend/resume; recreating audio stream.")
                        self.request_restart()
                    self.last_supervisor_tick = now

                    if self.restart_requested.is_set():
                        self.restart_requested.clear()
                        self._recover_stream("manual restart request")

                    self._consume_tray_command()
                    device_info = self._find_target_device()
                    if device_info is None:
                        self._close_stream()
                        self.stream_device_id = None
                        self.current_device_label = "nenhum"
                        self.state = AppState.WAITING_FOR_DEVICE
                        self.status_line = "Aguardando Philips TAB4000"
                        self.backoff_index = 0
                    else:
                        device_id, device_name = device_info
                        self.current_device_label = device_name
                        if self.stream is None or self.stream_device_id != device_id:
                            self.state = AppState.OPENING_STREAM
                            self.status_line = f"Abrindo stream para {device_name}"
                            self._open_stream(device_id)
                            self.stream_device_id = device_id
                            self.backoff_index = 0
                        else:
                            self._watchdog_stream(device_name)
                    self._publish_status()
                except Exception as exc:
                    LOGGER.exception("Supervisor failure: %s", exc)
                    self._recover_stream(str(exc))
                time.sleep(poll_interval)
        finally:
            self._close_stream()
            comtypes.CoUninitialize()

    def _watchdog_stream(self, device_name: str) -> None:
        if self.stream is None:
            return
        last_callback_time, last_callback_sample = self.pulse_planner.get_last_callback_snapshot()
        active_flag = True
        try:
            active_flag = bool(self.stream.active)
        except Exception:
            active_flag = False
        stalled = (time.monotonic() - last_callback_time) > float(self.config["watchdog"]["callback_stall_seconds"])
        if stalled or not active_flag or last_callback_sample <= 0:
            self._recover_stream("callback stall or inactive stream")
            return
        if self.state != AppState.REAL_AUDIO_ACTIVE:
            self.state = AppState.RUNNING
            self.status_line = f"Ativo em {device_name}"

    def _recover_stream(self, reason: str) -> None:
        self.state = AppState.RECOVERING
        self.status_line = "Recuperando audio"
        LOGGER.warning("Recovering audio stream: %s", reason)
        self._close_stream()
        backoffs = list(self.config["watchdog"]["backoff_seconds"])
        delay = float(backoffs[min(self.backoff_index, len(backoffs) - 1)])
        self.backoff_index = min(self.backoff_index + 1, len(backoffs) - 1)
        time.sleep(delay)

    def _find_target_device(self) -> Optional[tuple[int, str]]:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
        keywords = [item.lower() for item in self.config["device"]["keywords"]]
        try:
            default_output = sd.default.device[1]
        except Exception:
            default_output = None
        candidates = []
        for index, device in enumerate(devices):
            if int(device["max_output_channels"]) < int(self.config["device"]["channels"]):
                continue
            hostapi_name = str(hostapis[int(device["hostapi"])]["name"])
            if self.config["device"]["prefer_wasapi"] and "wasapi" not in hostapi_name.lower():
                continue
            name = str(device["name"])
            lowered = name.lower()
            if any(keyword in lowered for keyword in keywords):
                priority = 0 if index == default_output else 1
                candidates.append((priority, index, name, hostapi_name))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], item[2].lower()))
        if self.config["debug"]["log_device_scan"]:
            LOGGER.info("Selected device %s via host API %s", candidates[0][2], candidates[0][3])
        return candidates[0][1], candidates[0][2]

    def _open_stream(self, device_id: int) -> None:
        self._close_stream()
        device_info = sd.query_devices(device_id, "output")
        sample_rate = int(float(device_info["default_samplerate"]) or float(self.config["device"]["sample_rate"]))
        channels = min(int(device_info["max_output_channels"]), int(self.config["device"]["channels"]))
        self.pulse_planner.reconfigure_stream(sample_rate, channels, float(self.config["amplitude_dbfs"]["current"]))
        wasapi_settings = sd.WasapiSettings(exclusive=False) if hasattr(sd, "WasapiSettings") else None

        def callback(outdata, frames, time_info, status):
            if status:
                LOGGER.warning("Stream status: %s", status)
            block_start = self.pulse_planner.last_callback_sample
            outdata.fill(0)
            self.pulse_planner.mix_into(outdata, frames, block_start)
            self.pulse_planner.update_position(block_start + frames)

        with self.stream_lock:
            stream = sd.OutputStream(
                device=device_id,
                samplerate=sample_rate,
                channels=channels,
                dtype=self.config["audio"]["dtype"],
                blocksize=int(self.config["device"]["block_size"]),
                latency=self.config["device"]["latency"],
                callback=callback,
                extra_settings=wasapi_settings,
            )
            stream.start()
            self.stream = stream
        self.state = AppState.RUNNING
        self.status_line = f"Ativo em {self.current_device_label}"
        LOGGER.info(
            "Output stream started on device id=%s name=%s samplerate=%s channels=%s",
            device_id,
            self.current_device_label,
            sample_rate,
            channels,
        )

    def _close_stream(self) -> None:
        with self.stream_lock:
            if self.stream is not None:
                try:
                    self.stream.stop()
                except Exception:
                    pass
                try:
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None

    def _run_command(self, args: list[str], ok_codes: set[int], log_errors: bool = True) -> bool:
        result = subprocess.run(args, capture_output=True, text=True, check=False)
        if result.returncode not in ok_codes and log_errors:
            LOGGER.warning(
                "Command failed rc=%s args=%s stdout=%s stderr=%s",
                result.returncode,
                args,
                result.stdout.strip(),
                result.stderr.strip(),
            )
        return result.returncode in ok_codes

    def _start_tray_process(self) -> None:
        if self.tray_process is not None and self.tray_process.poll() is None:
            return
        command = [str(Path(sys.executable).resolve()), "--tray-host", "--skip-startup-task"]
        if not getattr(sys, "frozen", False):
            command = [str(Path(sys.executable).with_name("pythonw.exe")), str(Path(__file__).resolve()), "--tray-host", "--skip-startup-task"]
        try:
            self.tray_process = subprocess.Popen(command, cwd=str(APP_DIR))
            self.tray_warning_logged = False
            LOGGER.info("Tray helper process started.")
        except Exception as exc:
            LOGGER.exception("Could not start tray helper process. Continuing without tray support.", exc_info=exc)
            self.tray_process = None
            self.tray_warning_logged = True

    def _stop_tray_process(self) -> None:
        if self.tray_process is None:
            return
        if self.tray_process.poll() is None:
            try:
                self.tray_process.terminate()
                self.tray_process.wait(timeout=5)
            except Exception:
                try:
                    self.tray_process.kill()
                except Exception:
                    pass
        self.tray_process = None

    def _check_tray_process(self) -> None:
        if self.tray_process is None:
            return
        if self.tray_process.poll() is not None and not self.tray_warning_logged:
            self.tray_warning_logged = True
            LOGGER.warning("Tray helper process exited unexpectedly. Audio engine will continue without tray support.")

    def _publish_status(self) -> None:
        if not self.tray_enabled:
            return
        try:
            atomic_write_json(
                STATUS_FILE,
                {
                    "status_line": self.status_line,
                    "current_device_label": self.current_device_label,
                    "state": self.state.value,
                    "updated_at": time.time(),
                },
            )
        except Exception as exc:
            LOGGER.exception("Could not publish tray status.", exc_info=exc)

    def _consume_tray_command(self) -> None:
        if not TRAY_COMMAND_FILE.exists():
            return
        payload = load_json_file(TRAY_COMMAND_FILE)
        try:
            TRAY_COMMAND_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        command = payload.get("command")
        if command == "restart":
            LOGGER.info("Audio restart requested by tray helper.")
            self.request_restart()
        elif command == "quit":
            LOGGER.info("Shutdown requested by tray helper.")
            self.stop()


def acquire_single_instance() -> int:
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    if not handle:
        return 0
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return 11
    lock_handle = LOCK_FILE.open("a+b")
    try:
        lock_handle.seek(0)
        lock_handle.write(b"0")
        lock_handle.flush()
        lock_handle.seek(0)
        msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        lock_handle.close()
        return 11
    instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            instance_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        instance_socket.bind(("127.0.0.1", INSTANCE_PORT))
        instance_socket.listen(1)
    except OSError:
        lock_handle.close()
        instance_socket.close()
        return 11
    acquire_single_instance.handle = handle
    acquire_single_instance.lock_handle = lock_handle
    acquire_single_instance.instance_socket = instance_socket
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--no-tray", action="store_true")
    parser.add_argument("--debug-seconds", type=float, default=0.0)
    parser.add_argument("--ensure-startup", action="store_true")
    parser.add_argument("--remove-startup", action="store_true")
    parser.add_argument("--cleanup-legacy", action="store_true")
    parser.add_argument("--skip-startup-task", action="store_true")
    parser.add_argument("--status-json", action="store_true")
    parser.add_argument("--tray-host", action="store_true")
    return parser.parse_args()


def build_status_snapshot(config: dict) -> dict:
    return {
        "app_name": APP_NAME,
        "config_file": str(CONFIG_FILE),
        "log_file": str(LOG_FILE),
        "scheduled_task": TASK_NAME,
        "limitations": config["limitations"]["physical_standby_detection"],
    }


def main() -> int:
    args = parse_args()
    config = load_config()
    configure_logging(config)
    if args.tray_host:
        LOGGER.info("Starting tray helper process.")
        return TrayController().run()
    mutex_rc = acquire_single_instance()
    if mutex_rc:
        LOGGER.info("Another %s instance is already running. Exiting.", APP_NAME)
        return mutex_rc
    if args.status_json:
        print(json.dumps(build_status_snapshot(config), indent=2, ensure_ascii=False))
        return 0

    app = KeepAliveApp(config, args)
    if args.cleanup_legacy:
        app.cleanup_legacy_versions()
        return 0
    if args.ensure_startup:
        app.ensure_startup_task()
        return 0
    if args.remove_startup:
        app.remove_startup_task()
        return 0

    try:
        return app.start()
    except KeyboardInterrupt:
        app.stop()
        return 0
    except Exception as exc:
        LOGGER.exception("Fatal error: %s", exc)
        app.stop()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
