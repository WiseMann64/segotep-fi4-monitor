"""Application entrypoint."""

from __future__ import annotations

import argparse
import logging
import signal
from pathlib import Path
from threading import Thread

from .config import ConfigError, default_config_path, load_config
from .device import Fi4Device
from .display_frequency import DisplayFrequencyPreference
from .logging_setup import configure_logging
from .runner import MonitorRunner
from .single_instance import SingleInstance
from .startup import StartupRegistration
from .temperature_unit import TemperatureUnitPreference
from .telemetry.libre_hardware_monitor import LibreHardwareMonitorProvider
from .tray import MonitorTray


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Segotep FI4 CPU telemetry monitor")
    parser.add_argument("--config", type=Path, help="path to a JSON config file")
    startup = parser.add_mutually_exclusive_group()
    startup.add_argument(
        "--install-startup", action="store_true", help="run this app at Windows sign-in"
    )
    startup.add_argument(
        "--remove-startup", action="store_true", help="stop running this app at Windows sign-in"
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config_path = (args.config or default_config_path()).resolve()
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2

    logger = configure_logging(config.logging)
    startup_arguments = ["--config", str(config_path)] if args.config else []
    startup = StartupRegistration(startup_arguments)

    try:
        if args.install_startup or args.remove_startup:
            enabled = args.install_startup
            startup.set_enabled(enabled)
            message = (
                "FI4 Monitor will run at Windows sign-in."
                if enabled
                else "FI4 Monitor was removed from Windows startup."
            )
            print(message)
            return 0
    except OSError as exc:
        print(f"Startup configuration error: {exc}")
        return 2

    instance = SingleInstance()
    if not instance.acquire():
        logger.info("another FI4 Monitor instance is already running")
        instance.close()
        return 0

    unit = TemperatureUnitPreference(config.temperature_unit, config_path)
    frequency = DisplayFrequencyPreference(config.display_interval_ms, config_path)
    telemetry = LibreHardwareMonitorProvider()
    runner = MonitorRunner(
        config,
        telemetry,
        Fi4Device(),
        logger,
        temperature_unit=lambda: unit.current,
        display_interval_ms=lambda: frequency.interval_ms,
    )
    tray = MonitorTray(unit, frequency, startup, runner.stop, logger)
    worker = Thread(target=runner.run, name="fi4-monitor-loop", daemon=True)

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("shutdown requested by signal %s", signum)
        runner.stop()
        tray.stop()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    try:
        worker.start()
        tray.run()
    finally:
        runner.stop()
        tray.stop()
        worker.join(timeout=5.0)
        if worker.is_alive():
            logger.warning("monitor loop did not stop within five seconds")
        instance.close()
        for handler in logger.handlers:
            handler.flush()
            if isinstance(handler, logging.FileHandler):
                handler.close()
    return 0
