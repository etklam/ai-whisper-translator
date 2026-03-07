import logging

from src.infrastructure.runtime.logging_config import configure_logging, is_develop_mode


def test_is_develop_mode_true_when_app_env_development():
    assert is_develop_mode({"APP_ENV": "development"}) is True


def test_is_develop_mode_true_when_app_debug_enabled():
    assert is_develop_mode({"APP_DEBUG": "1"}) is True


def test_is_develop_mode_false_by_default():
    assert is_develop_mode({}) is False


def test_configure_logging_sets_debug_level_in_develop_mode():
    enabled = configure_logging({"APP_ENV": "development"})
    assert enabled is True
    assert logging.getLogger().level == logging.DEBUG


def test_configure_logging_sets_info_level_in_normal_mode():
    enabled = configure_logging({})
    assert enabled is False
    assert logging.getLogger().level == logging.INFO
