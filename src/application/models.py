from dataclasses import dataclass, field


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


@dataclass
class TranslationFileResult:
    source_path: str
    success: bool
    output_path: str | None = None
    error_message: str | None = None


@dataclass
class ExecutionSummary:
    total_files: int
    successful_files: int
    failed_files: int
    output_paths: list[str]
    file_results: list[TranslationFileResult] = field(default_factory=list)


@dataclass
class QueueItemResult:
    queue_index: int
    item_kind: str
    source_value: str
    success: bool
    final_stage: str
    asr_output_path: str | None = None
    translation_output_path: str | None = None
    summary_output_path: str | None = None
    error_message: str | None = None

    @property
    def final_output_path(self) -> str | None:
        return self.summary_output_path or self.translation_output_path or self.asr_output_path


@dataclass(frozen=True)
class SourceQueueItem:
    kind: str
    value: str
