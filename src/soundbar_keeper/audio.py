from __future__ import annotations

import logging
import math
import threading
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from .config import AppConfig
from .devices import OutputDevice


@dataclass(slots=True)
class SignalProfile:
    frequencies_hz: np.ndarray
    phases: np.ndarray
    sample_rate_hz: float
    volume: float


class KeepAliveAudio:
    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger
        self._lock = threading.RLock()
        self._stream: sd.OutputStream | None = None
        self._device: OutputDevice | None = None
        self._signal_profile: SignalProfile | None = None
        self._last_callback_time = 0.0

    def update_config(self, config: AppConfig) -> None:
        with self._lock:
            should_restart = self._stream is not None and self._device is not None
            current_device = self._device
            self._config = config

            if should_restart and current_device is not None:
                self._stop_locked()
                self._start_locked(current_device)

    def start(self, device: OutputDevice, force_restart: bool = False) -> None:
        with self._lock:
            if self._stream is not None and self._device == device and not force_restart:
                return

            self._stop_locked()
            self._start_locked(device)

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def is_running(self) -> bool:
        with self._lock:
            return self._stream is not None

    def is_callback_stale(self, timeout_seconds: float) -> bool:
        with self._lock:
            if self._stream is None:
                return False
            return (time.monotonic() - self._last_callback_time) > timeout_seconds

    def _start_locked(self, device: OutputDevice) -> None:
        requested_sample_rate = max(self._config.sample_rate_hz, 8_000)
        fallback_sample_rate = max(device.default_samplerate, 8_000)
        candidate_sample_rates = [requested_sample_rate]

        if fallback_sample_rate not in candidate_sample_rates:
            candidate_sample_rates.append(fallback_sample_rate)

        channels = max(1, min(device.max_output_channels, 2))
        configured_frequencies = self._config.frequencies_hz or [self._config.tone_frequency_hz]

        for index, sample_rate in enumerate(candidate_sample_rates):
            frequencies = np.array(
                [min(float(frequency), sample_rate * 0.45) for frequency in configured_frequencies],
                dtype=np.float64,
            )
            self._signal_profile = SignalProfile(
                frequencies_hz=frequencies,
                phases=np.zeros(len(frequencies), dtype=np.float64),
                sample_rate_hz=float(sample_rate),
                volume=self._config.volume,
            )

            try:
                self._stream = sd.OutputStream(
                    device=device.index,
                    samplerate=sample_rate,
                    channels=channels,
                    dtype="float32",
                    blocksize=self._config.block_size,
                    latency="high",
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._device = device
                self._last_callback_time = time.monotonic()
                self._logger.info(
                    "Keep-alive V6 iniciado em '%s' (freqs=%s, volume=%.6f, sample_rate=%s, block_size=%s).",
                    device.name,
                    [round(value, 1) for value in frequencies.tolist()],
                    self._config.volume,
                    sample_rate,
                    self._config.block_size,
                )
                return
            except Exception:
                self._stream = None
                self._device = None
                self._signal_profile = None

                is_last_attempt = index == len(candidate_sample_rates) - 1
                if not is_last_attempt:
                    self._logger.warning(
                        "Falha ao iniciar audio V6 com sample_rate=%s em '%s'. Tentando fallback.",
                        sample_rate,
                        device.name,
                    )
                    continue

                self._logger.exception("Falha ao iniciar o stream V6 para '%s'.", device.name)

    def _stop_locked(self) -> None:
        if self._stream is None:
            return

        device_name = self._device.name if self._device else "desconhecido"
        try:
            self._stream.abort()
            self._stream.close()
            self._logger.info("Keep-alive V6 interrompido para '%s'.", device_name)
        except Exception:
            self._logger.exception("Falha ao encerrar o stream de audio.")
        finally:
            self._stream = None
            self._device = None
            self._signal_profile = None
            self._last_callback_time = 0.0

    def _audio_callback(self, outdata: np.ndarray, frames: int, _time: object, status: sd.CallbackFlags) -> None:
        signal_profile = self._signal_profile
        if signal_profile is None:
            outdata[:, :] = 0.0
            return

        if status:
            self._logger.debug("Status do callback de audio: %s", status)

        samples = np.arange(frames, dtype=np.float64)
        signal = np.zeros(frames, dtype=np.float64)

        for index, frequency in enumerate(signal_profile.frequencies_hz):
            phase_vector = signal_profile.phases[index] + (
                2.0 * math.pi * frequency * samples / signal_profile.sample_rate_hz
            )
            signal += np.sin(phase_vector)
            signal_profile.phases[index] = float(
                (phase_vector[-1] + (2.0 * math.pi * frequency / signal_profile.sample_rate_hz)) % (2.0 * math.pi)
            )

        signal /= max(1, len(signal_profile.frequencies_hz))
        envelope = 0.78 + 0.22 * math.sin(2.0 * math.pi * 0.37 * time.monotonic())
        signal *= signal_profile.volume * envelope

        mono = signal.astype(np.float32).reshape(-1, 1)
        outdata[:, :] = mono
        self._last_callback_time = time.monotonic()
