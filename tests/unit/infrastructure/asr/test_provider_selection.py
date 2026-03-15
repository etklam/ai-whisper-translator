import pytest

from src.infrastructure.asr.providers import create_asr_provider, resolve_asr_provider


def test_auto_provider_resolves_to_const_me_on_windows():
    assert resolve_asr_provider("auto", platform_name="win32") == "const_me"


def test_auto_provider_resolves_to_whisper_cpp_on_macos():
    assert resolve_asr_provider("auto", platform_name="darwin") == "whisper_cpp"


def test_const_me_provider_is_rejected_on_macos():
    with pytest.raises(ValueError, match="const_me.*darwin"):
        resolve_asr_provider("const_me", platform_name="darwin")


def test_windows_factory_creates_const_me_provider():
    provider = create_asr_provider(
        provider_name="const_me",
        platform_name="win32",
        model_path="C:/models/ggml-base.bin",
    )
    assert provider.__class__.__name__ == "ConstMeWhisperProvider"
