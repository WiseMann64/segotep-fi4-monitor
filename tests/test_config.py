import json

import pytest

from fi4_monitor.config import AppConfig, ConfigError, load_config


def test_default_config_is_safe() -> None:
    config = AppConfig()
    assert config.temperature_unit == "C"
    assert config.update_interval_ms == 200
    assert config.update_interval_s == 0.2


def test_config_loads_json(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {
                "temperature_unit": "F",
                "update_interval_ms": 150,
                "retry_interval_s": 2,
                "logging": False,
            }
        ),
        encoding="utf-8",
    )

    config = load_config(path)
    assert config.temperature_unit == "F"
    assert config.update_interval_ms == 150
    assert config.retry_interval_s == 2
    assert config.logging is False


def test_config_rejects_unsafe_refresh_interval() -> None:
    with pytest.raises(ConfigError):
        AppConfig.from_mapping({"update_interval_ms": 50})
