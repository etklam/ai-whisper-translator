from src.application.models import SourceQueueItem
from src.gui.presenters.queue_controller import pop_next_queue_item


def test_pop_next_queue_item_is_fifo():
    queue = [
        SourceQueueItem(kind="url", value="a"),
        SourceQueueItem(kind="file", value="b"),
    ]
    first = pop_next_queue_item(queue)
    second = pop_next_queue_item(queue)
    assert first.value == "a"
    assert second.value == "b"
    assert queue == []
