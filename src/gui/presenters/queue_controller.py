import threading

from src.application.models import SourceQueueItem


def build_source_queue(urls, files):
    queue = []
    for url in urls:
        queue.append(SourceQueueItem(kind="url", value=url))
    for path in files:
        queue.append(SourceQueueItem(kind="file", value=path))
    return queue


def pop_next_queue_item(queue_items):
    if not queue_items:
        return None
    return queue_items.pop(0)


def queue_status_text(current, total, status):
    return f"{current}/{total} - {status}"


class QueueController:
    def __init__(self):
        self._items = []
        self._lock = threading.Lock()
        self._total = 0
        self._is_running = False

    @property
    def total(self):
        return self._total

    @property
    def is_running(self):
        return self._is_running

    def items_snapshot(self):
        with self._lock:
            return list(self._items)

    def add_item(self, item):
        with self._lock:
            self._items.append(item)

    def add_items(self, items):
        with self._lock:
            self._items.extend(items)

    def clear(self):
        with self._lock:
            self._items = []
            self._total = 0
            self._is_running = False

    def can_start(self):
        with self._lock:
            return bool(self._items) and not self._is_running

    def start(self):
        with self._lock:
            if self._is_running or not self._items:
                return False
            self._total = len(self._items)
            self._is_running = True
            return True

    def stop(self):
        with self._lock:
            self._is_running = False

    def next_item(self):
        with self._lock:
            if not self._is_running:
                return None
            item = pop_next_queue_item(self._items)
            if item is None:
                self._is_running = False
                return None
            current_index = self._total - len(self._items)
            remaining = len(self._items)
            return current_index, remaining, item
