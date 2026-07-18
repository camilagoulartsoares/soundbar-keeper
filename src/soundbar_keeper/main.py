from __future__ import annotations

import argparse
import threading
from dataclasses import replace

from .audio import KeepAliveAudio
from .config import AppConfig, ConfigManager
from .devices import get_default_output_device, list_output_devices, matches_target_device
from .logger import configure_logging
from .resources import CONFIG_PATH, LOGS_DIR
from .tray import SystemTray
from .windows import SingleInstanceGuard, WindowsPowerManager, WindowsStartupManager, open_path


class SoundbarKeeperApp:
    def __init__(self) -> None:
        self._logger = configure_logging("INFO")
        self._config_manager = ConfigManager(logger=self._logger)
        self._config = self._config_manager.load()
        self._logger = configure_logging(self._config.log_level)
        self._startup_manager = WindowsStartupManager()
        self._single_instance = SingleInstanceGuard()
        self._power_manager = WindowsPowerManager()
        self._audio = KeepAliveAudio(self._config, self._logger)
        self._tray = SystemTray(self)
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="device-monitor",
            daemon=True,
        )
        self._state_lock = threading.RLock()
        self._paused = self._config.start_paused
        self._status_text = "Inicializando"

    def run(self) -> None:
        if not self._single_instance.acquire():
            self._logger.warning("Outra instancia do Soundbar Keeper ja esta em execucao.")
            return

        self._apply_startup_configuration()
        self._log_output_devices()
        self._monitor_thread.start()
        self._tray.refresh()

        try:
            self._tray.run()
        finally:
            self.shutdown()
            if self._monitor_thread.is_alive():
                self._monitor_thread.join(timeout=2)
            self._single_instance.release()

    def shutdown(self) -> None:
        if self._stop_event.is_set():
            return

        self._logger.info("Encerrando o aplicativo.")
        self._stop_event.set()
        self._audio.stop()
        self._power_manager.refresh(False)

    def open_config(self) -> None:
        open_path(CONFIG_PATH)

    def open_logs_directory(self) -> None:
        open_path(LOGS_DIR)

    def toggle_pause(self) -> None:
        with self._state_lock:
            self._paused = not self._paused
            paused = self._paused

        if paused:
            self._audio.stop()
            self._set_status("Pausado manualmente")
            self._logger.info("Aplicativo pausado manualmente.")
        else:
            self._set_status("Retomando monitoramento")
            self._logger.info("Aplicativo retomado manualmente.")

    def is_paused(self) -> bool:
        with self._state_lock:
            return self._paused

    def is_autostart_enabled(self) -> bool:
        return self._startup_manager.is_enabled()

    def toggle_autostart(self) -> None:
        self._config = replace(
            self._config,
            auto_start_with_windows=not self._config.auto_start_with_windows,
        )
        self._config_manager.save(self._config)
        self._apply_startup_configuration()
        self._logger.info(
            "Inicializacao com Windows %s.",
            "ativada" if self._config.auto_start_with_windows else "desativada",
        )

    def get_status_text(self) -> str:
        with self._state_lock:
            return self._status_text

    def _monitor_loop(self) -> None:
        self._logger.info("Loop de monitoramento iniciado.")

        while not self._stop_event.is_set():
            try:
                refreshed_config = self._config_manager.reload_if_changed()
                if refreshed_config is not None:
                    self._handle_config_reload(refreshed_config)

                self._power_manager.refresh(self._config.keep_pc_awake and not self.is_paused())

                if self.is_paused():
                    self._audio.stop()
                    self._set_status("Pausado manualmente")
                else:
                    self._evaluate_default_output()
            except Exception:
                self._logger.exception("Erro inesperado no loop principal.")
                self._set_status("Erro no monitoramento")

            self._tray.refresh()
            self._stop_event.wait(self._config.check_interval_seconds)

        self._logger.info("Loop de monitoramento encerrado.")

    def _evaluate_default_output(self) -> None:
        device = get_default_output_device(logger=self._logger)
        if device is None:
            self._audio.stop()
            self._set_status("Nenhuma saida padrao detectada")
            return

        if matches_target_device(device, self._config.device_name_patterns):
            if self._audio.is_callback_stale(self._config.watchdog_seconds):
                self._logger.warning("Watchdog detectou stream travado em '%s'. Reiniciando.", device.name)
                self._audio.start(device, force_restart=True)
                self._set_status(f"Recuperando audio em {device.name}")
                return

            self._audio.start(device)
            self._set_status(f"Ativo em {device.name}")
            return

        self._audio.stop()
        self._set_status(f"Em espera: {device.name}")

    def _handle_config_reload(self, config: AppConfig) -> None:
        self._config = config
        self._logger = configure_logging(config.log_level)
        self._audio.update_config(config)
        self._apply_startup_configuration()
        self._logger.info("Configuracao recarregada com sucesso.")

    def _apply_startup_configuration(self) -> None:
        if self._config.auto_start_with_windows:
            script_path = self._startup_manager.install()
            self._logger.debug("Script de inicializacao atualizado em %s", script_path)
        else:
            self._startup_manager.uninstall()

    def _log_output_devices(self) -> None:
        devices = list_output_devices(logger=self._logger)
        if not devices:
            self._logger.warning("Nenhum dispositivo de saida foi identificado.")
            return

        for device in devices:
            self._logger.info(
                "Saida disponivel: index=%s | name=%s | hostapi=%s | channels=%s | sample_rate=%s",
                device.index,
                device.name,
                device.hostapi,
                device.max_output_channels,
                device.default_samplerate,
            )

    def _set_status(self, status: str) -> None:
        with self._state_lock:
            self._status_text = status


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Soundbar Keeper")
    parser.add_argument("--install-startup", action="store_true", help="Registra o app na inicializacao do Windows.")
    parser.add_argument("--uninstall-startup", action="store_true", help="Remove o app da inicializacao do Windows.")
    parser.add_argument("--print-config-path", action="store_true", help="Exibe o caminho do arquivo de configuracao.")
    parser.add_argument("--list-devices", action="store_true", help="Lista os dispositivos de saida disponiveis.")
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    startup_manager = WindowsStartupManager()

    if args.install_startup:
        print(startup_manager.install())
        return

    if args.uninstall_startup:
        startup_manager.uninstall()
        return

    if args.print_config_path:
        print(CONFIG_PATH)
        return

    if args.list_devices:
        logger = configure_logging("INFO")
        for device in list_output_devices(logger=logger):
            print(
                f"index={device.index} | name={device.name} | hostapi={device.hostapi} | "
                f"channels={device.max_output_channels} | sample_rate={device.default_samplerate}"
            )
        return

    app = SoundbarKeeperApp()
    app.run()


if __name__ == "__main__":
    main()
