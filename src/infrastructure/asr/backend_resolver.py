def normalize_platform_name(platform_name: str) -> str:
    value = (platform_name or "").strip().lower()
    if value in {"windows", "win", "nt"}:
        return "win32"
    if value in {"macos", "osx"}:
        return "darwin"
    return value


def resolve_backends(platform: str, gpu_caps: dict) -> list[str]:
    platform = normalize_platform_name(platform)
    if platform == "win32":
        order = ["cuda", "hip", "vulkan", "cpu"]
    elif platform == "darwin":
        order = ["metal_coreml", "cpu"]
    else:
        order = ["vulkan", "cpu"]

    available = [backend for backend in order if backend == "cpu" or gpu_caps.get(backend, False)]
    return available if available else ["cpu"]
