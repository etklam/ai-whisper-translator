def resolve_backends(platform: str, gpu_caps: dict) -> list[str]:
    if platform == "win32":
        order = ["cuda", "hip", "vulkan", "cpu"]
    elif platform == "darwin":
        order = ["metal_coreml", "cpu"]
    else:
        order = ["vulkan", "cpu"]

    available = [backend for backend in order if backend == "cpu" or gpu_caps.get(backend, False)]
    return available if available else ["cpu"]
