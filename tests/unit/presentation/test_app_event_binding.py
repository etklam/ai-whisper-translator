import pytest
import tkinter as tk

from src.gui.app import App


def test_app_has_coordinator_reference():
    try:
        app = App()
    except tk.TclError:
        pytest.skip("Tk not available in test environment")
    assert hasattr(app, "coordinator")
    app.destroy()
