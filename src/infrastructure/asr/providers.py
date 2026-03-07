class NullASRProvider:
    def transcribe(self, input_path: str) -> list[dict]:
        return []
