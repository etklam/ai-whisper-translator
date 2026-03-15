from __future__ import annotations

from pathlib import Path

import pysrt


def load_srt(path: str | Path, *, encoding: str = "utf-8") -> pysrt.SubRipFile:
    source_path = Path(path)
    with source_path.open("r", encoding=encoding) as handle:
        return pysrt.SubRipFile.from_string(handle.read(), path=str(source_path), encoding=encoding)


def save_srt(subs: pysrt.SubRipFile, path: str | Path, *, encoding: str = "utf-8", eol: str | None = None) -> None:
    output_path = Path(path)
    with output_path.open("w", encoding=encoding) as handle:
        subs.write_into(handle, eol=eol)
