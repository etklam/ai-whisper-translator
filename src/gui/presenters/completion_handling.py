from dataclasses import dataclass
import os


COMPLETION_MARKER = "翻譯完成"
OUTPUT_PREFIX = "檔案已成功保存為:"


@dataclass
class FileTranslationUpdate:
    appended_status_text: str
    remove_index: int | None = None
    final_status_text: str | None = None
    dialog_text: str | None = None
    reset_progress: bool = False


@dataclass
class TranslationCompletionState:
    status_text: str
    dialog_text: str
    clear_workspace: bool
    reset_progress: bool = True


def append_status_text(current_text: str, message: str) -> str:
    if not current_text:
        return message
    return f"{current_text}\n{message}"


def extract_completed_output_path(message: str) -> str | None:
    if OUTPUT_PREFIX not in message:
        return None
    path = message.split(OUTPUT_PREFIX, 1)[-1].strip()
    return path or None


def find_matching_file_index(file_paths: list[str], completed_output_path: str | None) -> int | None:
    if not completed_output_path:
        return None

    completed_basename = os.path.basename(completed_output_path)
    for index, path in enumerate(file_paths):
        if os.path.basename(path) == completed_basename:
            return index
    return None


def resolve_file_translation_update(
    *,
    message: str,
    current_status_text: str,
    file_paths: list[str],
    auto_clean_workspace: bool,
    get_text,
) -> FileTranslationUpdate:
    appended_status_text = append_status_text(current_status_text, message)
    if COMPLETION_MARKER not in message:
        return FileTranslationUpdate(appended_status_text=appended_status_text)

    remove_index = None
    remaining_files = len(file_paths)

    if auto_clean_workspace:
        remove_index = find_matching_file_index(
            file_paths,
            extract_completed_output_path(message),
        )
        if remove_index is not None:
            remaining_files -= 1

    if auto_clean_workspace and remaining_files == 0:
        final_status = get_text("workspace_cleaned")
        return FileTranslationUpdate(
            appended_status_text=appended_status_text,
            remove_index=remove_index,
            final_status_text=final_status,
            dialog_text=final_status,
            reset_progress=True,
        )

    if not auto_clean_workspace:
        final_status = get_text("all_complete")
        return FileTranslationUpdate(
            appended_status_text=appended_status_text,
            final_status_text=final_status,
            dialog_text=final_status,
            reset_progress=True,
        )

    return FileTranslationUpdate(
        appended_status_text=appended_status_text,
        remove_index=remove_index,
    )


def resolve_translation_completion(summary, *, auto_clean_workspace: bool, get_text) -> TranslationCompletionState:
    if auto_clean_workspace:
        status_text = get_text("workspace_cleaned")
        return TranslationCompletionState(
            status_text=status_text,
            dialog_text=status_text,
            clear_workspace=True,
        )

    return TranslationCompletionState(
        status_text=f"{get_text('all_complete')} (ok={summary.successful_files}, failed={summary.failed_files})",
        dialog_text=get_text("all_complete"),
        clear_workspace=False,
    )
