from src.infrastructure.asr.backend_resolver import resolve_backends


def test_windows_backend_priority():
    result = resolve_backends(platform="win32", gpu_caps={"cuda": True, "hip": True, "vulkan": True})
    assert result == ["cuda", "hip", "vulkan", "cpu"]


def test_cpu_fallback_always_present():
    result = resolve_backends(platform="win32", gpu_caps={"cuda": False, "hip": False, "vulkan": False})
    assert result == ["cpu"]
