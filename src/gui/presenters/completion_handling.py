from dataclasses import dataclass, field
import os


@dataclass
class TranslationCompletionState:
    status_text: str
    dialog_text: str
    clear_workspace: bool
    reset_progress: bool = True
    remove_indices: list[int] = field(default_factory=list)
def find_matching_file_index(file_paths: list[str], completed_output_path: str | None) -> int | None:
    if not completed_output_path:
        return None

    completed_basename = os.path.basename(completed_output_path)
    for index, path in enumerate(file_paths):
        if os.path.basename(path) == completed_basename:
            return index
    return None


def find_matching_source_index(file_paths: list[str], source_path: str | None) -> int | None:
    if not source_path:
        return None
    for index, path in enumerate(file_paths):
        if path == source_path:
            return index
    return find_matching_file_index(file_paths, source_path)


def resolve_translation_completion(summary, *, auto_clean_workspace: bool, get_text, file_paths: list[str] | None = None) -> TranslationCompletionState:
    remove_indices: list[int] = []
    if auto_clean_workspace and file_paths:
        for result in getattr(summary, "file_results", []) or []:
            if not result.success:
                continue
            remove_index = find_matching_source_index(file_paths, result.source_path)
            if remove_index is not None:
                remove_indices.append(remove_index)

    if auto_clean_workspace and summary.failed_files > 0:
        status_text = get_text("partial_complete").format(summary.successful_files, summary.failed_files)
        return TranslationCompletionState(
            status_text=status_text,
            dialog_text=status_text,
            clear_workspace=False,
            remove_indices=sorted(set(remove_indices), reverse=True),
        )

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
