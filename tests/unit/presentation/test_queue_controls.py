from src.gui.app import _queue_status_text


def test_queue_status_text():
    assert _queue_status_text(1, 3, "transcribing") == "1/3 - transcribing"
