from src.application.models import TranslationRequest


def build_translation_request(
    *,
    file_paths: list[str],
    source_lang: str,
    target_lang: str,
    model_name: str,
    ui_language: str,
    parallel_requests: int,
    replace_original: bool,
    use_alt_prompt: bool,
    clean_before_translate: bool = False,
    output_conflict_policy: str = "rename",
) -> TranslationRequest:
    return TranslationRequest(
        file_paths=file_paths,
        source_lang=source_lang,
        target_lang=target_lang,
        model_name=model_name,
        ui_language=ui_language,
        parallel_requests=parallel_requests,
        clean_before_translate=clean_before_translate,
        replace_original=replace_original,
        use_alt_prompt=use_alt_prompt,
        output_conflict_policy=output_conflict_policy,
    )


def run_translation_request(coordinator, request: TranslationRequest, *, done_callback=None):
    if coordinator is None:
        raise RuntimeError("Translation coordinator is not configured")
    return coordinator.run_async(request, callback=done_callback)
