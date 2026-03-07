from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient


def test_translate_text_returns_content_on_valid_response(monkeypatch):
    client = OllamaTranslationClient("http://localhost:11434/v1/chat/completions")
    payload = {"choices": [{"message": {"content": "你好"}}]}

    class DummyResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            import json

            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=30: DummyResponse())
    assert client.translate_text("hello", "繁體中文", "m", "p") == "你好"
