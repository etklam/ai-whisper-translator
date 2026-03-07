from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider


def test_returns_default_prompt_when_file_missing(tmp_path):
    provider = JsonPromptProvider(str(tmp_path / "missing.json"))
    prompt = provider.get_prompt(use_alt_prompt=False)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
