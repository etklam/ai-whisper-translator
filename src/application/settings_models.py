from dataclasses import asdict, dataclass


@dataclass
class AppSettings:
    ui_language: str = "zh_tw"
    translation_engine_key: str = "ollama"
    source_lang: str = ""
    target_lang: str = ""
    model_name: str = ""
    parallel_requests: str = ""
    openai_endpoint: str = ""
    summary_prompt_zh_tw: str = ""
    summary_prompt_zh_cn: str = ""
    summary_prompt_en: str = ""
    translation_prompt_zh_tw: str = ""
    translation_prompt_zh_cn: str = ""
    translation_prompt_en: str = ""
    alt_translation_prompt_zh_tw: str = ""
    alt_translation_prompt_zh_cn: str = ""
    alt_translation_prompt_en: str = ""
    enable_translation: bool = False
    enable_summary: bool = False
    ai_engine_collapsed: bool = True
    clean_mode: bool = False
    debug_mode: bool = False
    auto_clean_workspace: bool = True
    replace_original: bool = False
    use_alt_prompt: bool = False
    output_to_source: bool = False
    asr_model_path: str = ""
    asr_provider: str = "auto"
    use_gpu: bool = False
    gpu_backend: str = ""
    asr_language: str = ""
    output_format: str = ""
    asr_output_path: str = ""

    @staticmethod
    def _coerce_bool(value, default: bool) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on"}:
                return True
            if normalized in {"0", "false", "no", "off", ""}:
                return False
        if value is None:
            return default
        return bool(value)

    @classmethod
    def from_dict(cls, raw: dict) -> "AppSettings":
        if not isinstance(raw, dict):
            return cls()

        normalized = {}
        for field_name in cls.__dataclass_fields__:
            default_value = getattr(cls, field_name)
            value = raw.get(field_name)
            if isinstance(default_value, bool):
                normalized[field_name] = cls._coerce_bool(value, default_value)
            elif value is None:
                normalized[field_name] = default_value
            else:
                normalized[field_name] = str(value) if isinstance(default_value, str) else value
        return cls(**normalized)

    def to_dict(self) -> dict:
        return asdict(self)
