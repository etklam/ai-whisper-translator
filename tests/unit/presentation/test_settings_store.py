from src.gui.config.settings_store import build_default_settings


def test_windows_default_asr_provider_is_const_me():
    payload = build_default_settings(platform_name="win32")
    assert payload["asr_provider"] == "const_me"


def test_macos_default_asr_provider_is_whisper_cpp():
    payload = build_default_settings(platform_name="darwin")
    assert payload["asr_provider"] == "whisper_cpp"
