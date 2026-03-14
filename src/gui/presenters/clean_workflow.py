from dataclasses import dataclass


@dataclass
class CleanProgress:
    current_file: int
    total_files: int
    progress_percent: float
    total_cleaned: int
    total_subtitles: int


@dataclass
class CleanWorkflowSummary:
    total_files: int
    total_cleaned: int
    total_subtitles: int


def run_clean_workflow(file_paths: list[str], cleaner, *, create_backup: bool, on_progress=None) -> CleanWorkflowSummary:
    total_cleaned = 0
    total_subtitles = 0
    total_files = len(file_paths)

    for index, file_path in enumerate(file_paths, start=1):
        result = cleaner(file_path, create_backup=create_backup)
        total_cleaned += int(result["cleaned"])
        total_subtitles += int(result["total"])

        if on_progress is not None:
            on_progress(
                CleanProgress(
                    current_file=index,
                    total_files=total_files,
                    progress_percent=(index / total_files) * 100,
                    total_cleaned=total_cleaned,
                    total_subtitles=total_subtitles,
                )
            )

    return CleanWorkflowSummary(
        total_files=total_files,
        total_cleaned=total_cleaned,
        total_subtitles=total_subtitles,
    )
