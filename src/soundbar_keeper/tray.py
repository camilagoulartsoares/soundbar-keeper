from __future__ import annotations

from typing import Protocol

import pystray
from PIL import Image, ImageDraw

from .resources import APP_NAME, ICON_PATH


class TrayController(Protocol):
    def get_status_text(self) -> str: ...

    def is_paused(self) -> bool: ...

    def toggle_pause(self) -> None: ...

    def open_config(self) -> None: ...

    def open_logs_directory(self) -> None: ...

    def is_autostart_enabled(self) -> bool: ...

    def toggle_autostart(self) -> None: ...

    def shutdown(self) -> None: ...


class SystemTray:
    def __init__(self, controller: TrayController) -> None:
        self._controller = controller
        self._icon = pystray.Icon(
            name="soundbar-keeper",
            title=APP_NAME,
            icon=self._load_icon(),
            menu=self._build_menu(),
        )

    def run(self) -> None:
        self._icon.run()

    def stop(self) -> None:
        self._icon.stop()

    def refresh(self) -> None:
        self._icon.title = f"{APP_NAME} | {self._controller.get_status_text()}"
        self._icon.update_menu()

    def _build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(
                lambda _item: self._controller.get_status_text(),
                lambda _icon, _item: None,
                enabled=False,
            ),
            pystray.MenuItem("Abrir configuracao", self._on_open_config),
            pystray.MenuItem("Abrir pasta de logs", self._on_open_logs),
            pystray.MenuItem(
                "Iniciar com o Windows",
                self._on_toggle_autostart,
                checked=lambda _item: self._controller.is_autostart_enabled(),
            ),
            pystray.MenuItem(
                lambda _item: "Retomar" if self._controller.is_paused() else "Pausar",
                self._on_toggle_pause,
            ),
            pystray.MenuItem("Fechar", self._on_shutdown),
        )

    def _on_open_config(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._controller.open_config()

    def _on_open_logs(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._controller.open_logs_directory()

    def _on_toggle_pause(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._controller.toggle_pause()
        self.refresh()

    def _on_toggle_autostart(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._controller.toggle_autostart()
        self.refresh()

    def _on_shutdown(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._controller.shutdown()
        self.stop()

    def _load_icon(self) -> Image.Image:
        if ICON_PATH.exists():
            try:
                return Image.open(ICON_PATH)
            except Exception:
                pass

        return _build_fallback_icon()


def _build_fallback_icon(size: int = 64) -> Image.Image:
    image = Image.new("RGBA", (size, size), (22, 33, 44, 255))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(27, 110, 194, 255))
    draw.polygon([(18, 34), (28, 26), (28, 42)], fill=(255, 255, 255, 255))
    draw.rectangle((28, 24, 36, 44), fill=(255, 255, 255, 255))
    draw.arc((30, 18, 48, 50), start=300, end=60, fill=(255, 255, 255, 255), width=3)
    draw.arc((34, 12, 56, 56), start=300, end=60, fill=(255, 255, 255, 180), width=3)

    return image
