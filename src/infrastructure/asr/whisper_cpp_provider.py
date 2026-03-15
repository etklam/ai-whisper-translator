class WhisperCppProvider:
    def __init__(
        self,
        model_path: str,
        library_path: str | None = None,
        use_gpu: bool = False,
        gpu_backend: str = "auto",
        fallback_to_cpu: bool = True,
        **_: object,
    ):
        self.model_path = model_path
        self.library_path = library_path
        self.use_gpu = use_gpu
        self.gpu_backend = gpu_backend
        self.fallback_to_cpu = fallback_to_cpu
        self._last_detected_language = None

    def build_transcriber(self):
        from src.asr.whisper_transcriber import Transcriber

        return Transcriber(
            model_path=self.model_path,
            library_path=self.library_path,
            use_gpu=self.use_gpu,
            gpu_backend=self.gpu_backend,
            fallback_to_cpu=self.fallback_to_cpu,
        )

    def load_model(self):
        with self.build_transcriber() as transcriber:
            transcriber.load_model()

    def get_detected_language(self):
        return self._last_detected_language

    def transcribe(
        self,
        input_path: str,
        language=None,
        n_threads: int = 4,
        print_progress: bool = False,
    ):
        with self.build_transcriber() as transcriber:
            segments = transcriber.transcribe_file(
                audio_path=input_path,
                language=language,
                n_threads=n_threads,
                print_progress=print_progress,
            )
            if transcriber.wrapper is not None and transcriber.ctx is not None:
                self._last_detected_language = transcriber.wrapper.get_detected_language(transcriber.ctx)
            return segments
