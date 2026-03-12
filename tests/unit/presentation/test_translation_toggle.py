from src.gui.app import _should_translate


def test_should_translate():
    assert _should_translate(True) is True
    assert _should_translate(False) is False
