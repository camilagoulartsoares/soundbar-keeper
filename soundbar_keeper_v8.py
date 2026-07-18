import ctypes
import json
import math
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pystray
import sounddevice as sd
from PIL import Image, ImageDraw

APP_NAME = "SoundbarKeeperV8UltraBurst"
APP_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "SoundbarKeeperV8"
APP_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "soundbar_keeper_v8.log"

DEFAULT_CONFIG = {
    "device_keywords": ["Philips", "TAB4000"],
    "sample_rate": 48000,
    "block_size": 960,
    "pulse_interval_seconds": 20.0,
    "pulse_duration_ms": 8.0,
    "frequencies_hz": [19200.0, 19500.0, 19800.0],
    "amplitude": 0.000020,
    "channels": 2,
    "check_interval_seconds": 3,
    "keep_windows_awake": True,
    "double_pulse": False,
    "double_pulse_gap_ms": 70.0
}

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
kernel32 = ctypes.windll.kernel32

running = True
paused = False
stream = None
stream_lock = threading.Lock()
status_text = "Iniciando..."


def log(message: str) -> None:
    try:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} - {message}\n")
    except Exception:
        pass


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        merged = DEFAULT_CONFIG.copy()
        merged.update(data)
        return merged
    except Exception as exc:
        log(f"Erro ao ler configuração: {exc}")
        return DEFAULT_CONFIG.copy()


config = load_config()


class UltraBurstGenerator:
    """Mantém o fluxo Bluetooth aberto e injeta rajadas ultracurtas e suavizadas."""

    def __init__(self):
        self.sr = int(config["sample_rate"])
        self.interval_samples = max(1, int(float(config["pulse_interval_seconds"]) * self.sr))
        self.pulse_samples = max(16, int(float(config["pulse_duration_ms"]) / 1000.0 * self.sr))
        self.position = 0
        self.frequencies = [float(x) for x in config["frequencies_hz"]]
        self.amplitude = float(config["amplitude"])
        self.double_pulse = bool(config.get("double_pulse", False))
        self.double_gap_samples = int(float(config.get("double_pulse_gap_ms", 70.0)) / 1000.0 * self.sr)

    def _one_pulse(self, absolute_positions: np.ndarray, pulse_start: int, frequency: float) -> np.ndarray:
        rel = absolute_positions - pulse_start
        active = (rel >= 0) & (rel < self.pulse_samples)
        signal = np.zeros(len(absolute_positions), dtype=np.float64)
        if not np.any(active):
            return signal
        p = rel[active].astype(np.float64)
        # Blackman: bordas ainda mais suaves que Hann, reduz clique/transiente audível.
        envelope = 0.42 - 0.5 * np.cos(2.0 * math.pi * p / max(1, self.pulse_samples - 1)) + 0.08 * np.cos(4.0 * math.pi * p / max(1, self.pulse_samples - 1))
        phase = 2.0 * math.pi * frequency * p / self.sr
        signal[active] = self.amplitude * envelope * np.sin(phase)
        return signal

    def callback(self, outdata, frames, time_info, status):
        if status:
            log(f"Áudio: {status}")
        positions = np.arange(self.position, self.position + frames, dtype=np.int64)
        cycle = positions // self.interval_samples
        cycle_start = cycle * self.interval_samples

        signal = np.zeros(frames, dtype=np.float64)
        unique_cycles = np.unique(cycle)
        for c in unique_cycles:
            start = int(c * self.interval_samples)
            freq = self.frequencies[int(c) % len(self.frequencies)]
            signal += self._one_pulse(positions, start, freq)
            if self.double_pulse:
                signal += self._one_pulse(positions, start + self.pulse_samples + self.double_gap_samples, freq)

        mono = signal.astype(np.float32)
        outdata[:] = mono[:, None]
        self.position += frames


def acquire_single_instance() -> bool:
    mutex = kernel32.CreateMutexW(None, False, "Local\\SoundbarKeeperV8UltraBurstMutex")
    if not mutex:
        return True
    if kernel32.GetLastError() == 183:
        return False
    acquire_single_instance.mutex = mutex
    return True


def get_default_output():
    try:
        output_index = sd.default.device[1]
        info = sd.query_devices(output_index, "output")
        return int(output_index), str(info["name"])
    except Exception as exc:
        log(f"Não foi possível consultar a saída padrão: {exc}")
        return None, ""


def target_is_selected(name: str) -> bool:
    lowered = name.lower()
    return any(str(k).lower() in lowered for k in config["device_keywords"])


def stop_stream():
    global stream
    with stream_lock:
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception:
                pass
            stream = None


def start_stream(device_index: int):
    global stream
    stop_stream()
    generator = UltraBurstGenerator()
    candidate = sd.OutputStream(
        device=device_index,
        samplerate=int(config["sample_rate"]),
        channels=int(config["channels"]),
        dtype="float32",
        blocksize=int(config["block_size"]),
        latency="high",
        callback=generator.callback,
    )
    candidate.start()
    with stream_lock:
        stream = candidate


def worker():
    global status_text
    last_device = None
    while running:
        try:
            if config.get("keep_windows_awake", True):
                kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

            if paused:
                stop_stream()
                status_text = "Pausado"
                time.sleep(1)
                continue

            device_index, device_name = get_default_output()
            if device_index is None:
                stop_stream()
                last_device = None
                status_text = "Sem saída de áudio"
            elif target_is_selected(device_name):
                restart_needed = stream is None or last_device != device_index
                if not restart_needed and stream is not None:
                    try:
                        restart_needed = not stream.active
                    except Exception:
                        restart_needed = True
                if restart_needed:
                    start_stream(device_index)
                    last_device = device_index
                    log(f"UltraBurst iniciado em: {device_name}")
                status_text = f"UltraBurst ativo — {device_name}"
            else:
                stop_stream()
                last_device = None
                status_text = f"Aguardando Philips — atual: {device_name or 'desconhecida'}"
        except Exception as exc:
            stop_stream()
            last_device = None
            status_text = "Erro — veja o log"
            log(f"Erro no worker: {exc}")
        time.sleep(float(config["check_interval_seconds"]))

    stop_stream()
    kernel32.SetThreadExecutionState(ES_CONTINUOUS)


def create_icon_image(active=True):
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    fill = (70, 150, 220, 255) if active else (130, 130, 130, 255)
    draw.rounded_rectangle((8, 18, 56, 46), radius=9, fill=fill)
    draw.arc((18, 22, 46, 42), 200, 340, fill=(255, 255, 255, 255), width=3)
    return image


def toggle_pause(icon, item):
    global paused
    paused = not paused
    icon.icon = create_icon_image(not paused)
    icon.update_menu()


def open_log(icon, item):
    if not LOG_FILE.exists():
        LOG_FILE.write_text("Nenhum erro registrado.\n", encoding="utf-8")
    os.startfile(str(LOG_FILE))


def open_config(icon, item):
    os.startfile(str(CONFIG_FILE))


def quit_app(icon, item):
    global running
    running = False
    stop_stream()
    icon.stop()


def pause_label(item):
    return "Retomar" if paused else "Pausar"


def status_label(item):
    return status_text


def main():
    if not acquire_single_instance():
        return
    threading.Thread(target=worker, daemon=True).start()
    menu = pystray.Menu(
        pystray.MenuItem(status_label, None, enabled=False),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(pause_label, toggle_pause),
        pystray.MenuItem("Abrir configurações", open_config),
        pystray.MenuItem("Abrir log", open_log),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Fechar", quit_app),
    )
    icon = pystray.Icon(APP_NAME, create_icon_image(True), "Soundbar Keeper V8 UltraBurst", menu)
    icon.run()


if __name__ == "__main__":
    main()
