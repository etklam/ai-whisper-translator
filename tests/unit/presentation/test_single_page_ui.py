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
    app.destroy()
