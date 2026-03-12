from src.gui.app import _pop_next_queue_item


def test_pop_next_queue_item_is_fifo():
    queue = [
        {"kind": "url", "value": "a"},
        {"kind": "file", "value": "b"},
    ]
    first = _pop_next_queue_item(queue)
    second = _pop_next_queue_item(queue)
    assert first["value"] == "a"
    assert second["value"] == "b"
    assert queue == []
