import os
from dataclasses import dataclass
from urllib.parse import urlparse, urlunparse

from src.domain.errors import ValidationError


DEFAULT_OPENAI_ENDPOINT = "http://localhost:11434/v1/chat/completions"
REMOTE_ENDPOINT_OPT_IN_ENV = "ALLOW_REMOTE_AI_ENDPOINTS"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class EndpointResolution:
    endpoint: str
    is_local: bool
    remote_allowed: bool


def normalize_openai_endpoint(endpoint: str | None) -> str:
    raw = (endpoint or DEFAULT_OPENAI_ENDPOINT).strip().rstrip("/")
    if not raw:
        raw = DEFAULT_OPENAI_ENDPOINT
    if raw.endswith("/v1/chat/completions"):
        return raw
    if raw.endswith("/chat/completions"):
        return raw
    if raw.endswith("/v1"):
        return f"{raw}/chat/completions"
    return f"{raw}/v1/chat/completions"


def build_models_endpoint(endpoint: str | None) -> str:
    base = normalize_openai_endpoint(endpoint).rstrip("/")
    if base.endswith("/v1/chat/completions"):
        return f"{base[:-len('/chat/completions')]}/models"
    return f"{base}/models"


def is_local_endpoint(endpoint: str | None) -> bool:
    normalized = normalize_openai_endpoint(endpoint)
    parsed = urlparse(normalized)
    return (parsed.hostname or "").lower() in LOCAL_HOSTS


def remote_endpoints_allowed(env: dict[str, str] | None = None) -> bool:
    environment = env or os.environ
    return str(environment.get(REMOTE_ENDPOINT_OPT_IN_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}


def validate_openai_endpoint(endpoint: str | None, *, env: dict[str, str] | None = None) -> EndpointResolution:
    normalized = normalize_openai_endpoint(endpoint)
    local = is_local_endpoint(normalized)
    remote_allowed = remote_endpoints_allowed(env)
    if not local and not remote_allowed:
        raise ValidationError(
            "Remote AI endpoints are disabled by default. "
            f"Set {REMOTE_ENDPOINT_OPT_IN_ENV}=1 to allow: {normalized}"
        )
    return EndpointResolution(endpoint=normalized, is_local=local, remote_allowed=remote_allowed)


def redact_endpoint(endpoint: str | None) -> str:
    normalized = normalize_openai_endpoint(endpoint)
    parsed = urlparse(normalized)
    if not parsed.password and not parsed.username:
        return normalized
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse(parsed._replace(netloc=netloc))
