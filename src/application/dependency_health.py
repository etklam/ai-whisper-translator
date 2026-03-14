from dataclasses import dataclass
import importlib.util


@dataclass(frozen=True)
class DependencyStatus:
    name: str
    available: bool
    detail: str = ""


def check_yt_dlp() -> DependencyStatus:
    available = importlib.util.find_spec("yt_dlp") is not None
    detail = "importable" if available else "not installed"
    return DependencyStatus(name="yt_dlp", available=available, detail=detail)
