from pathlib import Path

from src.domain.errors import ValidationError


def normalize_path(path: str | Path) -> Path:
    value = Path(path).expanduser()
    try:
        return value.resolve(strict=False)
    except RuntimeError:
        return value.absolute()


def ensure_existing_file(path: str | Path, *, allowed_suffixes: tuple[str, ...] | None = None) -> Path:
    resolved = normalize_path(path)
    if not resolved.exists():
        raise ValidationError(f"File does not exist: {resolved}")
    if not resolved.is_file():
        raise ValidationError(f"Path is not a file: {resolved}")
    if allowed_suffixes and resolved.suffix.lower() not in {suffix.lower() for suffix in allowed_suffixes}:
        raise ValidationError(f"Unsupported file type: {resolved}")
    return resolved


def ensure_output_directory(path: str | Path) -> Path:
    resolved = normalize_path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    if not resolved.is_dir():
        raise ValidationError(f"Output directory is not a directory: {resolved}")
    return resolved


def ensure_output_file_path(path: str | Path, *, allowed_parent: str | Path | None = None) -> Path:
    resolved = normalize_path(path)
    if allowed_parent is not None:
        parent = ensure_output_directory(allowed_parent)
        if resolved.parent != parent:
            raise ValidationError(f"Output path escapes expected directory: {resolved}")
    else:
        ensure_output_directory(resolved.parent)
    return resolved
