from pathlib import Path


class ConstMeWhisperProvider:
    def __init__(self, model_path: str, runtime_dir: str | None = None, dll_path: str | None = None, **_: object):
        self.model_path = model_path
        self.runtime_dir = runtime_dir
        self.dll_path = dll_path
        self._runtime_path: Path | None = None

    def _resolve_runtime_path(self) -> Path:
        if self.dll_path:
            runtime_path = Path(self.dll_path)
            if runtime_path.exists():
                return runtime_path
            raise FileNotFoundError(f"Const-me runtime DLL not found: {runtime_path}")

        if self.runtime_dir:
            runtime_dir = Path(self.runtime_dir)
            candidates = [
                runtime_dir / "Whisper.dll",
                runtime_dir / "whisper.dll",
            ]
            for candidate in candidates:
                if candidate.exists():
                    return candidate
            raise FileNotFoundError(f"Const-me runtime DLL not found under: {runtime_dir}")

        raise FileNotFoundError("Const-me runtime directory or DLL path is required")

    def load_model(self):
        model_path = Path(self.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Const-me model file not found: {model_path}")

        self._runtime_path = self._resolve_runtime_path()
        return self._runtime_path

    def get_detected_language(self):
        return None

    def transcribe(
        self,
        input_path: str,
        language=None,
        n_threads: int = 4,
        print_progress: bool = False,
    ) -> list[dict]:
        if self._runtime_path is None:
            self.load_model()
        return []
