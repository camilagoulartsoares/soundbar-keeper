from __future__ import annotations

import logging
import threading

import numpy as np
import sounddevice as sd

from .config import AppConfig
from .devices import OutputDevice


class KeepAliveAudio:
    def __init__(self, config: AppConfig, logger: logging.Logger) -> None:
        self._config = config
        self._logger = logger
        self._lock = threading.RLock()
        self._stream: sd.OutputStream | None = None
        self._device: OutputDevice | None = None
        self._sample_cursor = 0
        self._sample_rate = config.sample_rate_hz
        self._frequency = config.tone_frequency_hz
        self._volume = config.volume
        self._channels = 2

    def update_config(self, config: AppConfig) -> None:
        with self._lock:
            should_restart = self._stream is not None and self._device is not None
            current_device = self._device
            self._config = config
            self._volume = config.volume

            if should_restart and current_device is not None:
                self._stop_locked()
                self._start_locked(current_device)

    def start(self, device: OutputDevice) -> None:
        with self._lock:
            if self._stream is not None and self._device == device:
                return

            self._stop_locked()
            self._start_locked(device)

    def stop(self) -> None:
        with self._lock:
            self._stop_locked()

    def is_running(self) -> bool:
        with self._lock:
            return self._stream is not None

    def _start_locked(self, device: OutputDevice) -> None:
        requested_sample_rate = max(self._config.sample_rate_hz, 8_000)
        fallback_sample_rate = max(device.default_samplerate, 8_000)
        candidate_sample_rates = [requested_sample_rate]

        if fallback_sample_rate not in candidate_sample_rates:
            candidate_sample_rates.append(fallback_sample_rate)

        channels = max(1, min(device.max_output_channels, 2))

        for index, sample_rate in enumerate(candidate_sample_rates):
            frequency = min(self._config.tone_frequency_hz, sample_rate * 0.45)
            self._sample_cursor = 0
            self._sample_rate = sample_rate
            self._frequency = frequency
            self._volume = self._config.volume
            self._channels = channels

            try:
                self._stream = sd.OutputStream(
                    device=device.index,
                    samplerate=sample_rate,
                    channels=channels,
                    dtype="float32",
                    callback=self._audio_callback,
                )
                self._stream.start()
                self._device = device
                self._logger.info(
                    "Keep-alive de audio iniciado em '%s' (freq=%.1fHz, volume=%.6f, sample_rate=%s).",
                    device.name,
                    frequency,
                    self._volume,
                    sample_rate,
                )
                return
            except Exception:
                self._stream = None
                self._device = None

                is_last_attempt = index == len(candidate_sample_rates) - 1
                if not is_last_attempt:
                    self._logger.warning(
                        "Falha ao iniciar audio com sample_rate=%s em '%s'. Tentando fallback.",
                        sample_rate,
                        device.name,
                    )
                    continue

                self._logger.exception("Falha ao iniciar o stream de audio para '%s'.", device.name)

    def _stop_locked(self) -> None:
        if self._stream is None:
            return

        device_name = self._device.name if self._device else "desconhecido"
        try:
            self._stream.stop()
            self._stream.close()
            self._logger.info("Keep-alive de audio interrompido para '%s'.", device_name)
        except Exception:
            self._logger.exception("Falha ao encerrar o stream de audio.")
        finally:
            self._stream = None
            self._device = None

    def _audio_callback(self, outdata: np.ndarray, frames: int, _time: object, status: sd.CallbackFlags) -> None:
        if status:
            self._logger.debug("Status do callback de audio: %s", status)

        positions = np.arange(frames, dtype=np.float32) + self._sample_cursor
        tone = self._volume * np.sin((2 * np.pi * self._frequency * positions) / self._sample_rate)
        self._sample_cursor = (self._sample_cursor + frames) % self._sample_rate

        outdata[:, :] = tone.reshape(-1, 1)
