from typing import Protocol


class ASRProvider(Protocol):
    def transcribe(self, input_path: str) -> list[dict]: ...
