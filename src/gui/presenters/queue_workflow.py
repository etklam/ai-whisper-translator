import logging
import tkinter as tk
from tkinter import messagebox

from src.application.models import QueueItemResult
from src.gui.presenters.queue_controller import queue_status_text


logger = logging.getLogger(__name__)


def queue_item_label(app, item, state_key="queue_pending", detail=None):
    state_text = app.get_text(state_key)
    label = f"[{state_text}] {item.kind}: {item.value}"
    if detail:
        return f"{label} -> {detail}"
    return label


def _queue_display_index(app, queue_index: int) -> int:
    return getattr(app, "_queue_run_start_index", 0) + queue_index - 1


def _set_queue_list_item_state(app, display_index: int, state_key: str, detail=None) -> None:
    if display_index < 0 or display_index >= len(getattr(app, "queue_display_items", [])):
        return
    item = app.queue_display_items[display_index]
    app.queue_list.delete(display_index)
    app.queue_list.insert(display_index, queue_item_label(app, item, state_key=state_key, detail=detail))


def _queue_run_status_text(app) -> str:
    results = getattr(app, "queue_run_results", [])
    total = len(results)
    failed = len([result for result in results if not result.success])
    successful = total - failed
    if failed:
        return app.get_text("queue_partial").format(successful, failed)
    return f"{app.get_text('queue_done')} (ok={successful}, failed={failed})"


def start_queue_processing(app) -> bool:
    logger.info("Start queue requested")
    if app.queue_controller.is_running:
        logger.warning("Queue already running, ignoring start request")
        return False
    if bool(app.enable_translation_var.get()):
        if not app._validate_translation_settings():
            return False
    if hasattr(app, "translation_prompt_text"):
        app._set_translation_prompt_for_language(
            app.current_language.get(),
            app.translation_prompt_text.get("1.0", tk.END),
        )
    if hasattr(app, "summary_prompt_text"):
        app._set_summary_prompt_for_language(
            app.current_language.get(),
            app.summary_prompt_text.get("1.0", tk.END),
        )
    if app.url_text.get("1.0", tk.END).strip():
        logger.debug("Adding pending URLs before starting queue")
        app.add_urls_to_queue()
    if not app.queue_controller.start():
        logger.warning("Queue is empty, cannot start")
        messagebox.showwarning(app.get_text("notice"), app.get_text("queue_empty"))
        return False
    app.queue_run_results = []
    app._queue_run_start_index = len(getattr(app, "queue_display_items", [])) - app.queue_controller.total
    logger.info("Starting queue processing total_items=%s", app.queue_controller.total)
    process_next_queue_item(app)
    return True


def stop_queue_processing(app) -> None:
    logger.info("Stop queue requested")
    app.queue_controller.stop()


def process_next_queue_item(app) -> None:
    if not app.queue_controller.is_running:
        logger.debug("Queue processing stopped by user")
        return
    next_item = app.queue_controller.next_item()
    if next_item is None:
        app.status_label.config(text=_queue_run_status_text(app))
        logger.info("Queue processing completed")
        return
    current_index, remaining, item = next_item
    logger.debug(
        "Processing queue item index=%s/%s remaining=%s kind=%s",
        current_index,
        app.queue_controller.total,
        remaining,
        item.kind,
    )
    app.status_label.config(
        text=queue_status_text(current_index, app.queue_controller.total, app.get_text("queue_processing"))
    )
    _set_queue_list_item_state(app, _queue_display_index(app, current_index), "queue_processing")
    app._run_queue_item(item, current_index)


def handle_queue_item_done(app, result: QueueItemResult) -> None:
    app.queue_run_results.append(result)
    display_index = _queue_display_index(app, result.queue_index)
    if result.success:
        app.status_label.config(
            text=queue_status_text(result.queue_index, app.queue_controller.total, app.get_text("queue_done"))
        )
        _set_queue_list_item_state(app, display_index, "queue_done", detail=result.final_output_path)
    else:
        app.status_label.config(
            text=f"{queue_status_text(result.queue_index, app.queue_controller.total, app.get_text('queue_failed'))}: {result.error_message}"
        )
        detail = f"{result.final_stage}: {result.error_message}" if result.error_message else result.final_stage
        _set_queue_list_item_state(app, display_index, "queue_failed", detail=detail)

    if app.queue_controller.is_running:
        process_next_queue_item(app)
