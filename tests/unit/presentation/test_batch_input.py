from src.gui.app import _parse_urls


def test_parse_urls_strips_empty_lines():
    text = "\nhttps://a\n\nhttps://b\n"
    assert _parse_urls(text) == ["https://a", "https://b"]
