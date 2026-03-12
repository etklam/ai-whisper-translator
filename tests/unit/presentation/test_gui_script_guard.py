import importlib


def test_gui_script_does_not_exit_on_import():
    try:
        module = importlib.import_module("test_gui")
        importlib.reload(module)
    except SystemExit as exc:
        raise AssertionError(f"test_gui should not call sys.exit on import: {exc}")
