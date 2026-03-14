import pytest
import tkinter as tk

from src.gui.app import App


def test_single_page_widgets_exist():
    try:
        app = App(coordinator=None, asr_coordinator=None)
    except tk.TclError:
        pytest.skip("Tk not available in test environment")
    assert hasattr(app, "url_text")
    assert hasattr(app, "select_audio_button")
    assert hasattr(app, "queue_list")
    assert hasattr(app, "enable_translation_var")
    assert hasattr(app, "openai_endpoint")
    assert hasattr(app, "model_combo")
    assert hasattr(app, "translation_prompt_text")
    assert hasattr(app, "asr_model_path")
    assert hasattr(app, "gpu_backend")
    assert hasattr(app, "asr_lang")
    assert hasattr(app, "output_format")
    assert hasattr(app, "source_lang")
    assert hasattr(app, "target_lang")
    assert hasattr(app, "translation_engine")
    assert hasattr(app, "replace_original_check")
    assert hasattr(app, "ai_engine_toggle_button")
    app.destroy()
