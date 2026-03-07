from src.utils.file_utils import clean_srt_file, ensure_backup_dir, get_output_path


class PysrtSubtitleRepository:
    def ensure_backup_dir(self, backup_path: str) -> None:
        ensure_backup_dir(backup_path)

    def get_output_path(self, file_path: str, target_lang: str, replace_original: bool = False) -> str:
        return get_output_path(file_path, target_lang, replace_original)

    def clean_srt_file(self, input_file: str, create_backup: bool = False) -> dict:
        return clean_srt_file(input_file, create_backup)
