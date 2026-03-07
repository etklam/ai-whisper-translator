from dataclasses import dataclass


@dataclass
class ProgressEvent:
    current: int
    total: int
    message: str = ""
