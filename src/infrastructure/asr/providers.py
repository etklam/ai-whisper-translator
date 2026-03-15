from src.infrastructure.asr.backend_resolver import normalize_platform_name
from src.infrastructure.asr.const_me_provider import ConstMeWhisperProvider
from src.infrastructure.asr.whisper_cpp_provider import WhisperCppProvider


def resolve_asr_provider(provider_name: str, platform_name: str) -> str:
    provider = (provider_name or "auto").strip().lower()
    platform = normalize_platform_name(platform_name)

    if provider == "auto":
        if platform == "win32":
            return "const_me"
        if platform == "darwin":
            return "whisper_cpp"
        return "whisper_cpp"

    if provider == "const_me" and platform != "win32":
        raise ValueError(f"Provider const_me is not supported on platform {platform}")

    if provider == "whisper_cpp" and platform == "win32":
        raise ValueError(f"Provider whisper_cpp is not supported on platform {platform}")

    return provider


def create_asr_provider(provider_name: str, platform_name: str, model_path: str, **kwargs: object):
    resolved_provider = resolve_asr_provider(provider_name, platform_name)
    if resolved_provider == "const_me":
        return ConstMeWhisperProvider(model_path=model_path, **kwargs)
    if resolved_provider == "whisper_cpp":
        return WhisperCppProvider(model_path=model_path, **kwargs)
    raise ValueError(f"Unsupported ASR provider: {resolved_provider}")


class NullASRProvider:
    def transcribe(self, input_path: str) -> list[dict]:
        return []
