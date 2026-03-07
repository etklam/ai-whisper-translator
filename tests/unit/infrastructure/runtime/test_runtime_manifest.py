from src.infrastructure.runtime.runtime_manifest import RuntimeManifest


def test_runtime_manifest_has_backend_order():
    m = RuntimeManifest(platform="win32")
    assert "cpu" in m.backend_priority
