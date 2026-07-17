from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Iterable

import sounddevice as sd


@dataclass(slots=True, frozen=True)
class OutputDevice:
    index: int
    name: str
    hostapi: str
    max_output_channels: int
    default_samplerate: int


def list_output_devices(logger: logging.Logger | None = None) -> list[OutputDevice]:
    try:
        devices = sd.query_devices()
        return [_build_device(device) for device in devices if int(device["max_output_channels"]) > 0]
    except Exception:
        if logger:
            logger.exception("Falha ao listar dispositivos de audio.")
        return []


def get_default_output_device(logger: logging.Logger | None = None) -> OutputDevice | None:
    try:
        device = sd.query_devices(kind="output")
        return _build_device(device)
    except Exception:
        if logger:
            logger.exception("Falha ao consultar o dispositivo de saida padrao.")
        return None


def matches_target_device(device: OutputDevice | None, patterns: Iterable[str]) -> bool:
    if device is None:
        return False

    device_name = _normalize_name(device.name)
    return any(_normalize_name(pattern) in device_name for pattern in patterns if pattern)


def _build_device(raw: dict[str, Any]) -> OutputDevice:
    hostapi_index = int(raw.get("hostapi", -1))
    hostapi_name = "unknown"

    try:
        if hostapi_index >= 0:
            hostapi_name = str(sd.query_hostapis(hostapi_index)["name"])
    except Exception:
        hostapi_name = "unknown"

    return OutputDevice(
        index=int(raw.get("index", -1)),
        name=str(raw.get("name", "Unknown output")),
        hostapi=hostapi_name,
        max_output_channels=int(raw.get("max_output_channels", 0)),
        default_samplerate=int(float(raw.get("default_samplerate", 44_100))),
    )


def _normalize_name(value: str) -> str:
    return " ".join(value.casefold().split())
