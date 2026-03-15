import os
import threading

from src.application.models import QueueItemResult
from src.application.path_validation import ensure_output_file_path
from src.gui.presenters.queue_controller import queue_status_text
from src.utils.srt_io import load_srt


def resolve_asr_output_path(app, audio_path, prefer_source_dir: bool = True):
    output_dir = app.asr_output_path.get().strip() or "transcriptions"
    if app.output_to_source_var.get() and prefer_source_dir and audio_path:
        source_dir = os.path.dirname(os.path.abspath(audio_path))
        if source_dir:
            output_dir = source_dir

    base_name = os.path.splitext(os.path.basename(audio_path))[0]
    ext = app.output_format.get()
    return str(ensure_output_file_path(os.path.join(output_dir, f"{base_name}.{ext}")))


def run_asr_request(app, audio_path, output_path):
    if not app.asr_coordinator:
        raise RuntimeError(app.get_text("asr_not_available"))

    from src.application.asr_coordinator import ASRRequest

    language = app._resolve_asr_language()

    request = ASRRequest(
        input_path=audio_path,
        output_path=output_path,
        model_path=app.asr_model_path.get(),
        language=language,
        use_gpu=app.use_gpu_var.get(),
        gpu_backend=app.gpu_backend.get(),
        n_threads=4,
        output_format=app.output_format.get(),
        max_retries=1,
    )
    app.asr_coordinator.run(request)


def run_translation_for_output(app, output_path, index):
    if not output_path.lower().endswith(".srt"):
        return True

    app.after(
        0,
        lambda: app.status_label.config(
            text=queue_status_text(index, app.queue_controller.total, app.get_text("queue_translating"))
        ),
    )

    def _on_done(summary):
        app.after(0, lambda: app._on_queue_translation_complete(output_path, index, summary))

    return bool(app._start_translation_request([output_path], done_callback=_on_done))


def run_summary_for_output(app, output_path, index, done_callback=None):
    if not output_path:
        if done_callback:
            app.after(0, lambda: done_callback(True, output_path))
        return

    def _load_text(path: str) -> str:
        if path.lower().endswith(".srt"):
            subs = load_srt(path)
            return "\n".join(sub.text for sub in subs)
        if path.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        return ""

    def _summary_output_path(path: str) -> str:
        base, _ext = os.path.splitext(path)
        return f"{base}.summary.txt"

    def _run():
        try:
            text = _load_text(output_path)
            if not text.strip():
                if done_callback:
                    app.after(0, lambda: done_callback(True, output_path))
                return
            prompt = app._get_summary_prompt()
            client = app._build_ollama_client()
            summary = client.translate_text(
                text=text,
                source_lang=None,
                target_lang="a concise summary in English",
                model_name=app.model_combo.get(),
                system_prompt=prompt,
            )
            out_path = _summary_output_path(output_path)
            with open(out_path, "w", encoding="utf-8") as handle:
                handle.write(summary.strip() + "\n")
            app.after(
                0,
                lambda: app.status_label.config(
                    text=queue_status_text(index, app.queue_controller.total, app.get_text("queue_summary_done"))
                ),
            )
            if done_callback:
                app.after(0, lambda: done_callback(True, out_path))
        except Exception as exc:
            message = f"Summary failed: {exc}"
            app.after(0, lambda msg=message: app.status_label.config(text=msg))
            if done_callback:
                app.after(0, lambda msg=message: done_callback(False, msg))

    app.after(
        0,
        lambda: app.status_label.config(
            text=queue_status_text(index, app.queue_controller.total, app.get_text("queue_summary"))
        ),
    )
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def run_queue_item(app, item, index):
    def _finish(result: QueueItemResult):
        app.after(0, lambda: app._on_queue_item_done(result))

    def _after_summary(success, message, *, asr_output_path=None, translation_output_path=None):
        if success:
            _finish(
                QueueItemResult(
                    queue_index=index,
                    item_kind=item.kind,
                    source_value=item.value,
                    success=True,
                    final_stage="summary",
                    asr_output_path=asr_output_path,
                    translation_output_path=translation_output_path,
                    summary_output_path=message,
                )
            )
            return
        _finish(
            QueueItemResult(
                queue_index=index,
                item_kind=item.kind,
                source_value=item.value,
                success=False,
                final_stage="summary",
                asr_output_path=asr_output_path,
                translation_output_path=translation_output_path,
                error_message=message,
            )
        )

    def _after_translation(success, next_output_path, error_message, *, asr_output_path=None):
        if not success:
            _finish(
                QueueItemResult(
                    queue_index=index,
                    item_kind=item.kind,
                    source_value=item.value,
                    success=False,
                    final_stage="translation",
                    asr_output_path=asr_output_path,
                    error_message=error_message or "Translation failed",
                )
            )
            return
        if app.enable_summary_var.get():
            run_summary_for_output(
                app,
                next_output_path,
                index,
                done_callback=lambda summary_success, summary_message: _after_summary(
                    summary_success,
                    summary_message,
                    asr_output_path=asr_output_path,
                    translation_output_path=next_output_path,
                ),
            )
            return
        _finish(
            QueueItemResult(
                queue_index=index,
                item_kind=item.kind,
                source_value=item.value,
                success=True,
                final_stage="translation",
                asr_output_path=asr_output_path,
                translation_output_path=next_output_path,
            )
        )

    def _run():
        current_stage = "download" if item.kind == "url" else "asr"
        asr_output_path = None
        try:
            if item.kind == "url":
                from src.asr.audio_downloader import AudioDownloader

                downloader = AudioDownloader(output_dir="downloads")
                audio_path = downloader.download_audio_to_wav(item.value)
            else:
                audio_path = item.value

            if not audio_path or not os.path.exists(audio_path):
                raise FileNotFoundError(app.get_text("audio_missing").format(audio_path))

            prefer_source_dir = item.kind == "file"
            current_stage = "asr"
            output_path = resolve_asr_output_path(app, audio_path, prefer_source_dir=prefer_source_dir)
            asr_output_path = output_path
            run_asr_request(app, audio_path, output_path)

            if app.enable_translation_var.get():
                current_stage = "translation"
                def _on_translation_done(summary):
                    actual_output_path = summary.output_paths[0] if getattr(summary, "output_paths", None) else output_path
                    success = summary.successful_files > 0 and summary.failed_files == 0
                    error_message = None
                    file_results = getattr(summary, "file_results", None) or []
                    if file_results and not success:
                        error_message = file_results[0].error_message

                    def _handle_translation_result():
                        app._on_queue_translation_complete(output_path, index, summary)
                        _after_translation(
                            success,
                            actual_output_path,
                            error_message or actual_output_path if not success else None,
                            asr_output_path=asr_output_path,
                        )

                    app.after(0, _handle_translation_result)

                if not app._start_translation_request([output_path], done_callback=_on_translation_done):
                    raise RuntimeError("Translation could not be started")
                return

            if app.enable_summary_var.get():
                current_stage = "summary"
                run_summary_for_output(
                    app,
                    output_path,
                    index,
                    done_callback=lambda summary_success, summary_message: _after_summary(
                        summary_success,
                        summary_message,
                        asr_output_path=asr_output_path,
                    ),
                )
                return

            _finish(
                QueueItemResult(
                    queue_index=index,
                    item_kind=item.kind,
                    source_value=item.value,
                    success=True,
                    final_stage="asr",
                    asr_output_path=output_path,
                )
            )
        except Exception as exc:
            error_msg = str(exc)
            _finish(
                QueueItemResult(
                    queue_index=index,
                    item_kind=item.kind,
                    source_value=item.value,
                    success=False,
                    final_stage=current_stage,
                    asr_output_path=asr_output_path,
                    error_message=error_msg,
                )
            )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
