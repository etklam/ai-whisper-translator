import shutil
import uuid
from pathlib import Path
from types import SimpleNamespace

from src.application.asr_coordinator import ASRCoordinator, ASRRequest


def test_asr_coordinator_passes_provider_name_to_factory(monkeypatch):
    temp_dir = Path(".tmp_test_artifacts") / f"asr_coordinator_{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    try:
        input_path = temp_dir / "input.wav"
        output_path = temp_dir / "output.srt"
        model_path = temp_dir / "ggml-base.bin"
        input_path.write_bytes(b"audio")
        model_path.write_bytes(b"model")

        captured = {}

        class FakeProvider:
            def load_model(self):
                return None

            def transcribe(self, input_path: str, language=None, n_threads=4, print_progress=False):
                return [
                    SimpleNamespace(
                        text="hello",
                        start=0,
                        end=1000,
                        no_speech_prob=0.0,
                    )
                ]

            def get_detected_language(self):
                return "en"

        def fake_create_asr_provider(provider_name: str, platform_name: str, model_path: str, **kwargs):
            captured["provider_name"] = provider_name
            captured["platform_name"] = platform_name
            captured["model_path"] = model_path
            captured["kwargs"] = kwargs
            return FakeProvider()

        monkeypatch.setattr(
            "src.infrastructure.asr.providers.create_asr_provider",
            fake_create_asr_provider,
        )

        coordinator = ASRCoordinator()
        summary = coordinator.run(
            ASRRequest(
                input_path=str(input_path),
                output_path=str(output_path),
                model_path=str(model_path),
                asr_provider="const_me",
            )
        )

        assert summary.successful_files == 1
        assert output_path.exists()
        assert captured["provider_name"] == "const_me"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
