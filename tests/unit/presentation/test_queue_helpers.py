from src.gui.app import _build_source_queue


def test_build_source_queue_preserves_order():
    urls = ["https://a", "https://b"]
    files = ["/tmp/1.wav", "/tmp/2.wav"]
    queue = _build_source_queue(urls, files)
    assert [item["kind"] for item in queue] == ["url", "url", "file", "file"]
    assert [item["value"] for item in queue] == ["https://a", "https://b", "/tmp/1.wav", "/tmp/2.wav"]
