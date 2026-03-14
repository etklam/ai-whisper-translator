from dataclasses import dataclass


@dataclass
class TranslationRequest:
    file_paths: list[str]
    source_lang: str
    target_lang: str
    model_name: str
    ui_language: str = "zh_tw"
    parallel_requests: int = 3
    clean_before_translate: bool = False
    replace_original: bool = False
    use_alt_prompt: bool = False
    max_retries: int = 1
    output_conflict_policy: str = "rename"
