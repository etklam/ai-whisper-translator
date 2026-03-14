import tkinter as tk


def next_language(current: str) -> str:
    if current == "zh_tw":
        return "zh_cn"
    if current == "zh_cn":
        return "en"
    return "zh_tw"


def apply_ui_language(app) -> None:
    app.title(app.get_text("window_title"))
    if hasattr(app, "hero_title_label"):
        app.hero_title_label.config(text=app.get_text("window_title"))
    if hasattr(app, "hero_meta_label"):
        app.hero_meta_label.config(text=app._pipeline_summary_text())
    if hasattr(app, "status_heading_label"):
        app.status_heading_label.config(text=app.get_text("workflow_status"))

    app.lang_button.config(text=app.get_text("switch_language"))
    if hasattr(app, "youtube_urls_label"):
        app.youtube_urls_label.config(text=app.get_text("youtube_urls"))
    if hasattr(app, "add_urls_button"):
        app.add_urls_button.config(text=app.get_text("add_urls_to_queue"))
    if hasattr(app, "select_audio_button"):
        app.select_audio_button.config(text=app.get_text("select_audio_files"))
    if hasattr(app, "clear_queue_button"):
        app.clear_queue_button.config(text=app.get_text("clear_queue"))
    if hasattr(app, "start_queue_button"):
        app.start_queue_button.config(text=app.get_text("start_queue"))
    if hasattr(app, "stop_queue_button"):
        app.stop_queue_button.config(text=app.get_text("stop_queue"))
    if hasattr(app, "enable_translation_check"):
        app.enable_translation_check.config(text=app.get_text("enable_translation"))
    if hasattr(app, "enable_summary_check"):
        app.enable_summary_check.config(text=app.get_text("enable_summary"))
    if hasattr(app, "sources_frame"):
        app.sources_frame.config(text=app.get_text("sources_section"))
    if hasattr(app, "queue_frame"):
        app.queue_frame.config(text=app.get_text("queue_section"))
    if hasattr(app, "asr_frame"):
        app.asr_frame.config(text=app.get_text("asr_section"))
    if hasattr(app, "translation_frame"):
        app.translation_frame.config(text=app.get_text("translation_section"))
    if hasattr(app, "output_frame"):
        app.output_frame.config(text=app.get_text("output_section"))
    if hasattr(app, "asr_model_frame"):
        app.asr_model_frame.config(text=app.get_text("whisper_model_section"))
    if hasattr(app, "transcribe_frame"):
        app.transcribe_frame.config(text=app.get_text("transcribe_section"))

    if hasattr(app, "target_lang_label"):
        app.target_lang_label.config(text=app.get_text("target_lang_label"))
    if hasattr(app, "source_lang_label"):
        app.source_lang_label.config(text=app.get_text("source_lang_label"))
    if hasattr(app, "translation_engine_label"):
        app.translation_engine_label.config(text=app.get_text("translation_engine_label"))
    if hasattr(app, "openai_endpoint_label"):
        app.openai_endpoint_label.config(text=app.get_text("openai_endpoint_label"))
    if hasattr(app, "openai_api_key_label"):
        app.openai_api_key_label.config(text=app.get_text("openai_api_key_label"))
    if hasattr(app, "summary_prompt_label"):
        app.summary_prompt_label.config(text=app.get_text("summary_prompt_label"))
    if hasattr(app, "translation_prompt_label"):
        app.translation_prompt_label.config(text=app.get_text("translation_prompt_label"))
    if hasattr(app, "alt_translation_prompt_label"):
        app.alt_translation_prompt_label.config(text=app.get_text("alt_translation_prompt_label"))
    if hasattr(app, "reset_translation_prompt_button"):
        app.reset_translation_prompt_button.config(text=app.get_text("reset_translation_prompt"))
    if hasattr(app, "reset_summary_prompt_button"):
        app.reset_summary_prompt_button.config(text=app.get_text("reset_summary_prompt"))
    if hasattr(app, "reset_alt_translation_prompt_button"):
        app.reset_alt_translation_prompt_button.config(text=app.get_text("reset_alt_translation_prompt"))
    if hasattr(app, "use_alt_prompt_check"):
        app.use_alt_prompt_check.config(text=app.get_text("use_alt_prompt"))
    if hasattr(app, "ai_engine_frame"):
        app.ai_engine_frame.config(text=app.get_text("ai_engine_section"))
    if hasattr(app, "ai_engine_toggle_button"):
        app.ai_engine_toggle_button.config(text=app._get_ai_engine_toggle_text())
    if hasattr(app, "menubar") and hasattr(app, "file_menu"):
        try:
            app.menubar.entryconfig(0, label=app.get_text("menu_file"))
            app.file_menu.entryconfig(0, label=app.get_text("menu_clean_srt"))
            app.file_menu.entryconfig(2, label=app.get_text("menu_exit"))
        except tk.TclError:
            pass
    if hasattr(app, "model_label"):
        app.model_label.config(text=app.get_text("model_label"))
    if hasattr(app, "parallel_label"):
        app.parallel_label.config(text=app.get_text("parallel_label"))

    if hasattr(app, "use_gpu_check"):
        app.use_gpu_check.config(text=app.get_text("use_gpu"))
    if hasattr(app, "gpu_backend_label"):
        app.gpu_backend_label.config(text=app.get_text("gpu_backend"))
    if hasattr(app, "asr_model_label"):
        app.asr_model_label.config(text=app.get_text("whisper_model_label"))
    if hasattr(app, "browse_model_button"):
        app.browse_model_button.config(text=app.get_text("browse"))
    if hasattr(app, "asr_lang_label"):
        app.asr_lang_label.config(text=app.get_text("asr_language_label"))
    if hasattr(app, "output_format_label"):
        app.output_format_label.config(text=app.get_text("output_format"))
    if hasattr(app, "asr_output_path_label"):
        app.asr_output_path_label.config(text=app.get_text("output_folder_label"))
    if hasattr(app, "browse_output_button"):
        app.browse_output_button.config(text=app.get_text("browse"))
    if hasattr(app, "open_output_button"):
        app.open_output_button.config(text=app.get_text("open_output_folder"))
    if hasattr(app, "output_to_source_check"):
        app.output_to_source_check.config(text=app.get_text("output_to_source"))
    if hasattr(app, "audio_path_label"):
        if app.selected_audio_path:
            app.audio_path_label.config(
                text=app.get_text("selected_file").format(app.selected_audio_path)
            )
        else:
            app.audio_path_label.config(text=app.get_text("selected_file_none"))

    if hasattr(app, "asr_lang"):
        app.asr_lang["values"] = app.translations[app.current_language.get()]["asr_language_options"]
        if app.asr_lang.get() not in app.asr_lang["values"]:
            app.asr_lang.set(app.asr_lang["values"][0])
    if hasattr(app, "source_lang"):
        source_values = app.translations[app.current_language.get()]["source_lang_options"]
        if app.translation_engine_key == "libretranslate":
            source_values = [v for v in source_values if not app._is_auto_lang(v)]
        app.source_lang["values"] = source_values
        if app.source_lang.get() not in source_values:
            app.source_lang.set(source_values[0] if source_values else "")
    if hasattr(app, "translation_engine"):
        app.translation_engine["values"] = app._get_engine_labels()
        app.translation_engine_var.set(app._label_for_engine(app.translation_engine_key))
    if hasattr(app, "target_lang"):
        app.target_lang["values"] = app.translations[app.current_language.get()]["target_lang_options"]
        if app.target_lang.get() not in app.target_lang["values"]:
            app.target_lang.set(app.target_lang["values"][0])
    app._refresh_summary_prompt_text()
    app._refresh_translation_prompt_text()
    app._refresh_alt_translation_prompt_text()
    app._save_config()
