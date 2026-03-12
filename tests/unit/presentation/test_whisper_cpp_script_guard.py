import importlib


def test_whisper_cpp_script_does_not_exit_on_import():
    try:
        module = importlib.import_module("test_whisper_cpp")
        importlib.reload(module)
    except SystemExit as exc:
        raise AssertionError(f"test_whisper_cpp should not call sys.exit on import: {exc}")
