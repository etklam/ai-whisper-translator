import logging
import os
import sys
from collections.abc import Mapping
from urllib.parse import urlparse, urlunparse

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


def redact_secret(value: str | None, *, keep_prefix: int = 3) -> str:
    if not value:
        return ""
    if len(value) <= keep_prefix:
        return "*" * len(value)
    return f"{value[:keep_prefix]}***"


def redact_endpoint(value: str | None) -> str:
    if not value:
        return ""
    parsed = urlparse(value)
    if not parsed.username and not parsed.password:
        return value
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))
