import logging
import os
import sys
from collections.abc import Mapping

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def is_develop_mode(env: Mapping[str, str] | None = None) -> bool:
    environment = env or os.environ
    app_env = str(environment.get("APP_ENV", "")).strip().lower()
    app_debug = str(environment.get("APP_DEBUG", "")).strip()
    return app_env == "development" or app_debug == "1"


def configure_logging(env: Mapping[str, str] | None = None) -> bool:
    develop_mode = is_develop_mode(env)
    level = logging.DEBUG if develop_mode else logging.INFO
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        datefmt=LOG_DATE_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    return develop_mode
