from src.infrastructure.asr.providers import create_asr_provider


def test_macos_factory_keeps_whisper_cpp_provider():
    provider = create_asr_provider(
        provider_name="whisper_cpp",
        platform_name="darwin",
        model_path="/tmp/ggml-base.bin",
    )
    assert provider.__class__.__name__ == "WhisperCppProvider"
