from typing import Protocol


class ASRProvider(Protocol):
    model_path: str

    def transcribe(self, input_path: str) -> list[dict]: ...
