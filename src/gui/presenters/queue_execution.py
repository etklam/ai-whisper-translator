import os
import threading

import pysrt

from src.application.path_validation import ensure_output_file_path
from src.gui.presenters.queue_controller import queue_status_text


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


def run_summary_for_output(app, output_path, index):
    if not output_path:
        return

    def _load_text(path: str) -> str:
        if path.lower().endswith(".srt"):
            subs = pysrt.open(path)
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
        except Exception as exc:
            message = f"Summary failed: {exc}"
            app.after(0, lambda msg=message: app.status_label.config(text=msg))

    app.after(
        0,
        lambda: app.status_label.config(
            text=queue_status_text(index, app.queue_controller.total, app.get_text("queue_summary"))
        ),
    )
    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def run_queue_item(app, item, index):
    def _run():
        try:
            if item["kind"] == "url":
                from src.asr.audio_downloader import AudioDownloader

                downloader = AudioDownloader(output_dir="downloads")
                audio_path = downloader.download_audio_to_wav(item["value"])
            else:
                audio_path = item["value"]

            if not audio_path or not os.path.exists(audio_path):
                raise FileNotFoundError(app.get_text("audio_missing").format(audio_path))

            prefer_source_dir = item.get("kind") == "file"
            output_path = resolve_asr_output_path(app, audio_path, prefer_source_dir=prefer_source_dir)
            run_asr_request(app, audio_path, output_path)

            if app.enable_summary_var.get():
                run_summary_for_output(app, output_path, index)

            if app.enable_translation_var.get():
                if not run_translation_for_output(app, output_path, index):
                    raise RuntimeError("Translation could not be started")

            app.after(0, lambda: app._on_queue_item_done(index, True, output_path))
        except Exception as exc:
            error_msg = str(exc)
            app.after(0, lambda msg=error_msg: app._on_queue_item_done(index, False, msg))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
