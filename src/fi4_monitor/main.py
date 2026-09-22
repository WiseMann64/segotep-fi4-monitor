"""Application entrypoint."""

from __future__ import annotations

import argparse
import logging
import signal
from pathlib import Path

from .config import ConfigError, load_config
from .device import Fi4Device
from .logging_setup import configure_logging
from .runner import MonitorRunner
from .single_instance import SingleInstance
from .telemetry.libre_hardware_monitor import LibreHardwareMonitorProvider


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Segotep FI4 CPU telemetry monitor")
    parser.add_argument("--config", type=Path, help="path to a JSON config file")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2

    logger = configure_logging(config.logging)
    instance = SingleInstance()
    if not instance.acquire():
        logger.info("another FI4 Monitor instance is already running")
        instance.close()
        return 0

    telemetry = LibreHardwareMonitorProvider()
    runner = MonitorRunner(config, telemetry, Fi4Device(), logger)

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("shutdown requested by signal %s", signum)
        runner.stop()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, request_stop)

    try:
        runner.run()
    finally:
        instance.close()
        for handler in logger.handlers:
            handler.flush()
            if isinstance(handler, logging.FileHandler):
                handler.close()
    return 0
