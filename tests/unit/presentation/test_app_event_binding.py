from src.gui.app import App


def test_app_has_coordinator_reference():
    app = App()
    assert hasattr(app, "coordinator")
    app.destroy()
