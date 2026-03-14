import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import os
import sys
import logging
import subprocess
import json
from typing import Any
from queue import Queue
import threading

from src.utils.file_utils import ensure_backup_dir, clean_srt_file

# 暫時禁用 tkinterdnd2（macOS 兼容性問題）
# TODO: 修復 tkinterdnd2 後重新啟用
TKDND_AVAILABLE = False
print("提示：拖放功能已暫時停用（macOS 兼容性）")

from src.translation.translation_thread import TranslationThread
from src.infrastructure.translation.libretranslate_client import LibreTranslateClient
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient

logger = logging.getLogger(__name__)

def _build_source_queue(urls, files):
    queue = []
    for url in urls:
        queue.append({"kind": "url", "value": url})
    for path in files:
        queue.append({"kind": "file", "value": path})
    return queue

def _parse_urls(text):
    return [line.strip() for line in text.splitlines() if line.strip()]

def _pop_next_queue_item(queue_items):
    if not queue_items:
        return None
    return queue_items.pop(0)

def _queue_item_label(item):
    return f"{item['kind']}: {item['value']}"

def _should_translate(flag):
    return bool(flag)

def _queue_status_text(current, total, status):
    return f"{current}/{total} - {status}"

ENGINE_KEYS = ["ollama", "libretranslate"]
CONFIG_FILENAME = ".config"

class App(tk.Tk):
    def __init__(self, coordinator=None, asr_coordinator=None):
        super().__init__()
        self.countdown_window = None
        self.coordinator = coordinator
        self.asr_coordinator = asr_coordinator
        logger.debug("App initialized coordinator_present=%s asr_coordinator_present=%s tkdnd_available=%s",
                    bool(coordinator), bool(asr_coordinator), TKDND_AVAILABLE)

        # 初始化語言設定
        self.current_language = tk.StringVar(value="zh_tw")  # 預設使用繁體中文
        self.translations = {
            "zh_tw": {
                "window_title": "AI 語音轉譯器",
                "select_files": "選擇 SRT 檔案",
                "select_folder": "文件夾批量新增",
                "source_lang_label": "原文語言:",
                "target_lang_label": "目標語言:",
                "translation_engine_label": "翻譯引擎:",
                "openai_endpoint_label": "OpenAI 端點:",
                "model_label": "選擇模型:",
                "parallel_label": "並行請求數:",
                "auto_clean": "翻譯前自動清理",
                "debug_mode": "調試模式",
                "clean_workspace": "翻譯後清理工作區",
                "replace_original": "取代原始檔案",
                "start_translation": "開始翻譯",
                "file_removed": "已從工作區移除選中的檔案",
                "no_files": "警告",
                "no_files_message": "請先選擇要翻譯的 SRT 檔案",
                "confirm": "確認",
                "replace_warning": "您選擇了取代原始檔案模式。\n這將會直接覆蓋原始的 SRT 檔案。\n原始檔案將會備份到 backup 資料夾。\n是否確定要繼續？",
                "cleaning": "正在清理檔案...",
                "cleaning_progress": "正在清理檔案 {}/{} ({:.1f}%)\n已清理 {}/{} 句字幕",
                "cleaning_complete": "清理完成！共清理 {}/{} 句字幕\n開始翻譯...",
                "translating": "正在翻譯 {} 個檔案...",
                "translation_progress": "正在翻譯第 {}/{} 句字幕 ({}%)",
                "all_complete": "所有檔案翻譯完成！",
                "workspace_cleaned": "所有檔案翻譯完成！工作區已清理。",
                "error": "錯誤",
                "error_message": "移除檔案時發生錯誤：{}",
                "source_lang_options": ["日文", "英文", "繁體中文", "簡體中文", "韓文", "法文", "德文", "西班牙文", "義大利文", "葡萄牙文", "俄文", "阿拉伯文", "印地文", "印尼文", "越南文", "泰文", "馬來文", "自動偵測"],
                "target_lang_options": ["繁體中文", "英文", "日文", "韓文", "法文", "德文", "西班牙文", "義大利文", "葡萄牙文", "俄文", "阿拉伯文", "印地文", "印尼文", "越南文", "泰文", "馬來文"],
                "translation_engine_options": ["Ollama（OpenAI 相容）", "LibreTranslate（免費）"],
                "switch_language": "切換語言",
                "fixed_lang_required": "請選擇固定原文語言（不可使用自動偵測）",
                "file_conflict_title": "檔案已存在",
                "file_conflict_message": "檔案 {} 已存在。\n請選擇處理方式：\n\n'覆蓋' = 覆蓋現有檔案\n'重新命名' = 自動重新命名\n'跳過' = 跳過此檔案",
                "overwrite": "覆蓋",
                "rename": "重新命名",
                "skip": "跳過",
                "auto_rename_countdown": "{} 秒後自動重新命名",
                # ASR translatons
                "asr_tab": "語音轉文字",
                "translate_tab": "字幕翻譯",
                "select_audio": "選擇音訊檔案",
                "youtube_url": "YouTube URL:",
                "sources_section": "來源",
                "youtube_urls": "YouTube URLs (一行一個):",
                "select_audio_files": "選擇音訊檔案（可多選）",
                "queue_section": "處理佇列",
                "add_urls_to_queue": "加入 URL 到佇列",
                "clear_queue": "清空佇列",
                "start_queue": "開始處理",
                "stop_queue": "停止",
                "asr_section": "ASR 設定",
                "translation_section": "翻譯（可選）",
                "enable_translation": "啟用翻譯",
                "output_section": "輸出設定",
                "download_from_youtube": "從 YouTube 下載",
                "whisper_model_label": "Whisper 模型:",
                "gpu_backend": "GPU 後端:",
                "gpu_backend_options": ["auto", "metal", "cuda", "hip", "vulkan", "opencl", "cpu"],
                "use_gpu": "使用 GPU 加速",
                "asr_language_label": "轉錄語言:",
                "asr_language_options": ["自動偵測", "英文", "繁體中文", "簡體中文", "日文", "韓文", "法文", "德文", "西班牙文"],
                "output_format": "輸出格式:",
                "output_format_options": ["srt", "txt", "json", "verbose"],
                "output_to_source": "輸出到原本位置（如有）",
                "open_output_folder": "開啟輸出資料夾",
                "start_asr": "開始轉錄",
                "asr_not_available": "ASR 功能不可用",
                "asr_not_available_msg": "Whisper transcriber not available. Please install whisper.cpp library and set up the model path.",
            },
            "zh_cn": {
                "window_title": "AI 语音转译器",
                "select_files": "选择 SRT 文件",
                "select_folder": "文件夹批量新增",
                "source_lang_label": "原文语言:",
                "target_lang_label": "目标语言:",
                "translation_engine_label": "翻译引擎:",
                "openai_endpoint_label": "OpenAI 端点:",
                "model_label": "选择模型:",
                "parallel_label": "并行请求数:",
                "auto_clean": "翻译前自动清理",
                "debug_mode": "调试模式",
                "clean_workspace": "翻译后清理工作区",
                "replace_original": "替换原始文件",
                "start_translation": "开始翻译",
                "file_removed": "已从工作区移除选中的文件",
                "no_files": "警告",
                "no_files_message": "请先选择要翻译的 SRT 文件",
                "confirm": "确认",
                "replace_warning": "您选择了替换原始文件模式。\n这将会直接覆盖原始的 SRT 文件。\n原始文件将会备份到 backup 文件夹。\n是否确定要继续？",
                "cleaning": "正在清理文件...",
                "cleaning_progress": "正在清理文件 {}/{} ({:.1f}%)\n已清理 {}/{} 句字幕",
                "cleaning_complete": "清理完成！共清理 {}/{} 句字幕\n开始翻译...",
                "translating": "正在翻译 {} 个文件...",
                "translation_progress": "正在翻译第 {}/{} 句字幕 ({}%)",
                "all_complete": "所有文件翻译完成！",
                "workspace_cleaned": "所有文件翻译完成！工作区已清理。",
                "error": "错误",
                "error_message": "移除文件时发生错误：{}",
                "source_lang_options": ["日文", "英文", "繁体中文", "简体中文", "韩文", "法文", "德文", "西班牙文", "意大利文", "葡萄牙文", "俄文", "阿拉伯文", "印地文", "印尼文", "越南文", "泰文", "马来文", "自动检测"],
                "target_lang_options": ["简体中文", "英文", "日文", "韩文", "法文", "德文", "西班牙文", "意大利文", "葡萄牙文", "俄文", "阿拉伯文", "印地文", "印尼文", "越南文", "泰文", "马来文"],
                "translation_engine_options": ["Ollama（OpenAI 相容）", "LibreTranslate（免费）"],
                "switch_language": "切换语言",
                "fixed_lang_required": "请选择固定原文语言（不可使用自动检测）",
                "file_conflict_title": "文件已存在",
                "file_conflict_message": "文件 {} 已存在。\n请选择处理方式：\n\n'覆盖' = 覆盖现有文件\n'重新命名' = 自动重新命名\n'跳过' = 跳过此文件",
                "overwrite": "覆盖",
                "rename": "重新命名",
                "skip": "跳过",
                "auto_rename_countdown": "{} 秒后自动重新命名",
                # ASR translatons
                "asr_tab": "语音转文字",
                "translate_tab": "字幕翻译",
                "select_audio": "选择音频文件",
                "youtube_url": "YouTube URL:",
                "sources_section": "来源",
                "youtube_urls": "YouTube URLs (一行一个):",
                "select_audio_files": "选择音频文件（可多选）",
                "queue_section": "处理队列",
                "add_urls_to_queue": "加入 URL 到队列",
                "clear_queue": "清空队列",
                "start_queue": "开始处理",
                "stop_queue": "停止",
                "asr_section": "ASR 设置",
                "translation_section": "翻译（可选）",
                "enable_translation": "启用翻译",
                "output_section": "输出设置",
                "download_from_youtube": "从 YouTube 下载",
                "whisper_model_label": "Whisper 模型:",
                "gpu_backend": "GPU 后端:",
                "gpu_backend_options": ["auto", "metal", "cuda", "hip", "vulkan", "opencl", "cpu"],
                "use_gpu": "使用 GPU 加速",
                "asr_language_label": "转录语言:",
                "asr_language_options": ["自动检测", "英文", "繁体中文", "简体中文", "日文", "韩文", "法文", "德文", "西班牙文"],
                "output_format": "输出格式:",
                "output_format_options": ["srt", "txt", "json", "verbose"],
                "output_to_source": "输出到原位置（如有）",
                "open_output_folder": "打开输出文件夹",
                "start_asr": "开始转录",
                "asr_not_available": "ASR 功能不可用",
                "asr_not_available_msg": "Whisper transcriber not available. Please install whisper.cpp library and set up the model path.",
            },
            "en": {
                "window_title": "ai-whisper-translator",
                "select_files": "Select SRT Files",
                "select_folder": "Add Folder",
                "source_lang_label": "Source Language:",
                "target_lang_label": "Target Language:",
                "translation_engine_label": "Translation Engine:",
                "openai_endpoint_label": "OpenAI Endpoint:",
                "model_label": "Select Model:",
                "parallel_label": "Parallel Requests:",
                "auto_clean": "Auto Clean Before Translation",
                "debug_mode": "Debug Mode",
                "clean_workspace": "Clean Workspace After Translation",
                "replace_original": "Replace Original File",
                "start_translation": "Start Translation",
                "file_removed": "Selected file has been removed from workspace",
                "no_files": "Warning",
                "no_files_message": "Please select SRT files first",
                "confirm": "Confirm",
                "replace_warning": "You have chosen to replace original files.\nThis will overwrite the original SRT files.\nOriginal files will be backed up to the backup folder.\nDo you want to continue?",
                "cleaning": "Cleaning files...",
                "cleaning_progress": "Cleaning files {}/{} ({:.1f}%)\nCleaned {}/{} subtitles",
                "cleaning_complete": "Cleaning complete! Cleaned {}/{} subtitles\nStarting translation...",
                "translating": "Translating {} files...",
                "translation_progress": "Translating subtitle {}/{} ({}%)",
                "all_complete": "All files have been translated!",
                "workspace_cleaned": "All files have been translated! Workspace has been cleaned.",
                "error": "Error",
                "error_message": "Error removing file: {}",
                "source_lang_options": ["Japanese", "English", "Traditional Chinese", "Simplified Chinese", "Korean", "French", "German", "Spanish", "Italian", "Portuguese", "Russian", "Arabic", "Hindi", "Indonesian", "Vietnamese", "Thai", "Malay", "Auto Detect"],
                "target_lang_options": ["Traditional Chinese", "English", "Japanese", "Korean", "French", "German", "Spanish", "Italian", "Portuguese", "Russian", "Arabic", "Hindi", "Indonesian", "Vietnamese", "Thai", "Malay"],
                "translation_engine_options": ["Ollama (OpenAI-Compatible)", "LibreTranslate (Free)"],
                "switch_language": "Switch Language",
                "fixed_lang_required": "Please choose a fixed source language (auto-detect is not allowed).",
                "file_conflict_title": "File Exists",
                "file_conflict_message": "File {} already exists.\nPlease choose an action:\n\n'Overwrite' = Replace existing file\n'Rename' = Auto rename\n'Skip' = Skip this file",
                "overwrite": "Overwrite",
                "rename": "Rename",
                "skip": "Skip",
                "auto_rename_countdown": "Auto rename in {} seconds",
                # ASR translatons
                "asr_tab": "ASR",
                "translate_tab": "Translate",
                "select_audio": "Select Audio File",
                "youtube_url": "YouTube URL:",
                "sources_section": "Sources",
                "youtube_urls": "YouTube URLs (one per line):",
                "select_audio_files": "Select Audio Files (multi-select)",
                "queue_section": "Queue",
                "add_urls_to_queue": "Add URLs to Queue",
                "clear_queue": "Clear Queue",
                "start_queue": "Start Processing",
                "stop_queue": "Stop",
                "asr_section": "ASR Settings",
                "translation_section": "Translation (Optional)",
                "enable_translation": "Enable Translation",
                "output_section": "Output",
                "download_from_youtube": "Download from YouTube",
                "whisper_model_label": "Whisper Model:",
                "gpu_backend": "GPU Backend:",
                "gpu_backend_options": ["auto", "metal", "cuda", "hip", "vulkan", "opencl", "cpu"],
                "use_gpu": "Use GPU Acceleration",
                "asr_language_label": "Transcribe Language:",
                "asr_language_options": ["Auto Detect", "English", "Traditional Chinese", "Simplified Chinese", "Japanese", "Korean", "French", "German", "Spanish"],
                "output_format": "Output Format:",
                "output_format_options": ["srt", "txt", "json", "verbose"],
                "output_to_source": "Output to Source Folder (if available)",
                "open_output_folder": "Open Output Folder",
                "start_asr": "Start Transcription",
                "asr_not_available": "ASR Not Available",
                "asr_not_available_msg": "Whisper transcriber not available. Please install whisper.cpp library and set up the model path.",
            }
        }

        self.title(self.get_text("window_title"))
        self.geometry("1280x860")

        # 只在有 tkinterdnd2 時啟用拖放功能
        if TKDND_AVAILABLE:
            self.drop_target_register(DND_FILES)
            self.dnd_bind('<<Drop>>', self.handle_drop)

        # 初始化變數
        self.clean_mode_var = tk.BooleanVar(value=False)
        self.debug_mode_var = tk.BooleanVar(value=False)
        self.auto_clean_workspace_var = tk.BooleanVar(value=True)
        self.replace_original_var = tk.BooleanVar(value=False)
        self.use_alt_prompt_var = tk.BooleanVar(value=False)  # Add this line
        self.output_to_source_var = tk.BooleanVar(value=False)
        self.translation_engine_key = "ollama"
        self.translation_engine_var = tk.StringVar(value="")
        self.free_translation_client = LibreTranslateClient()
        self.ollama_translation_client = OllamaTranslationClient()
        self.config_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", CONFIG_FILENAME)
        )
        self._config_traces_bound = False
        self.queue_items = []
        self.queue_items_lock = threading.Lock()
        self.queue_total = 0
        self.is_running = False

        self.create_widgets()
        self.create_clean_menu()
        self._bind_config_traces()
        self._load_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def get_text(self, key):
        """獲取當前語言的文字"""
        return self.translations[self.current_language.get()].get(key, key)

    def _get_openai_endpoint(self) -> str:
        if hasattr(self, "openai_endpoint"):
            value = (self.openai_endpoint.get() or "").strip()
            if value:
                return value
        return os.getenv("OPENAI_COMPAT_ENDPOINT") or os.getenv("OLLAMA_ENDPOINT") or ""

    def _get_engine_labels(self):
        return self.translations[self.current_language.get()].get("translation_engine_options", [])

    def _label_for_engine(self, engine_key: str) -> str:
        labels = self._get_engine_labels()
        if engine_key in ENGINE_KEYS:
            idx = ENGINE_KEYS.index(engine_key)
            if idx < len(labels):
                return labels[idx]
        return labels[0] if labels else engine_key

    def _resolve_engine_key(self, label: str | None) -> str:
        if not label:
            return self.translation_engine_key
        for lang, texts in self.translations.items():
            labels = texts.get("translation_engine_options", [])
            if label in labels:
                idx = labels.index(label)
                if idx < len(ENGINE_KEYS):
                    return ENGINE_KEYS[idx]
        return self.translation_engine_key

    def _is_auto_lang(self, selection: str) -> bool:
        return selection in {"自動偵測", "自动检测", "Auto Detect", "auto", "AUTO"}

    def _default_source_lang(self) -> str:
        options = self.translations[self.current_language.get()]["source_lang_options"]
        for option in options:
            if self._is_auto_lang(option):
                return option
        return options[0] if options else ""

    def _resolve_asr_language(self) -> str:
        """Resolve ASR language selection to a whisper.cpp language code or 'auto'."""
        selection = (self.asr_lang.get() or "").strip()
        language_map = {
            "英文": "en",
            "繁體中文": "zh",
            "簡體中文": "zh",
            "日文": "ja",
            "韓文": "ko",
            "法文": "fr",
            "德文": "de",
            "西班牙文": "es",
            "繁体中文": "zh",
            "简体中文": "zh",
            "日文": "ja",
            "韩文": "ko",
            "法文": "fr",
            "德文": "de",
            "西班牙文": "es",
            "English": "en",
            "Traditional Chinese": "zh",
            "Simplified Chinese": "zh",
            "Japanese": "ja",
            "Korean": "ko",
            "French": "fr",
            "German": "de",
            "Spanish": "es",
        }
        if selection in {"自動偵測", "自动检测", "Auto Detect", "auto", "AUTO"} or not selection:
            logger.debug("ASR language selection resolved to auto: %s", selection or "(empty)")
            return "auto"

        resolved = language_map.get(selection)
        if not resolved:
            logger.warning("Unrecognized ASR language selection: %s; falling back to auto", selection)
            return "auto"

        logger.debug("ASR language selection resolved: %s -> %s", selection, resolved)
        return resolved

    def switch_language(self):
        """切換語言"""
        current = self.current_language.get()
        if current == "zh_tw":
            new_language = "zh_cn"
        elif current == "zh_cn":
            new_language = "en"
        else:
            new_language = "zh_tw"
        self.current_language.set(new_language)
        logger.debug("UI language switched from=%s to=%s", current, new_language)
        self.update_ui_language()
        self._save_config()

    def update_ui_language(self):
        """更新UI語言"""
        # 更新視窗標題
        self.title(self.get_text("window_title"))
        
        # 更新語言切換按鈕
        self.lang_button.config(text=self.get_text("switch_language"))
        if hasattr(self, "youtube_urls_label"):
            self.youtube_urls_label.config(text=self.get_text("youtube_urls"))
        if hasattr(self, "add_urls_button"):
            self.add_urls_button.config(text=self.get_text("add_urls_to_queue"))
        if hasattr(self, "select_audio_button"):
            self.select_audio_button.config(text=self.get_text("select_audio_files"))
        if hasattr(self, "clear_queue_button"):
            self.clear_queue_button.config(text=self.get_text("clear_queue"))
        if hasattr(self, "start_queue_button"):
            self.start_queue_button.config(text=self.get_text("start_queue"))
        if hasattr(self, "stop_queue_button"):
            self.stop_queue_button.config(text=self.get_text("stop_queue"))
        if hasattr(self, "enable_translation_check"):
            self.enable_translation_check.config(text=self.get_text("enable_translation"))

        if hasattr(self, "target_lang_label"):
            self.target_lang_label.config(text=self.get_text("target_lang_label"))
        if hasattr(self, "source_lang_label"):
            self.source_lang_label.config(text=self.get_text("source_lang_label"))
        if hasattr(self, "translation_engine_label"):
            self.translation_engine_label.config(text=self.get_text("translation_engine_label"))
        if hasattr(self, "openai_endpoint_label"):
            self.openai_endpoint_label.config(text=self.get_text("openai_endpoint_label"))
        if hasattr(self, "model_label"):
            self.model_label.config(text=self.get_text("model_label"))
        if hasattr(self, "parallel_label"):
            self.parallel_label.config(text=self.get_text("parallel_label"))

        if hasattr(self, "use_gpu_check"):
            self.use_gpu_check.config(text=self.get_text("use_gpu"))
        if hasattr(self, "gpu_backend_label"):
            self.gpu_backend_label.config(text=self.get_text("gpu_backend"))
        if hasattr(self, "asr_lang_label"):
            self.asr_lang_label.config(text=self.get_text("asr_language_label"))
        if hasattr(self, "output_format_label"):
            self.output_format_label.config(text=self.get_text("output_format"))
        if hasattr(self, "open_output_button"):
            self.open_output_button.config(text=self.get_text("open_output_folder"))
        if hasattr(self, "output_to_source_check"):
            self.output_to_source_check.config(text=self.get_text("output_to_source"))

        if hasattr(self, "asr_lang"):
            self.asr_lang['values'] = self.translations[self.current_language.get()]["asr_language_options"]
            if self.asr_lang.get() not in self.asr_lang['values']:
                self.asr_lang.set(self.asr_lang['values'][0])
        if hasattr(self, "source_lang"):
            source_values = self.translations[self.current_language.get()]["source_lang_options"]
            if self.translation_engine_key == "libretranslate":
                source_values = [v for v in source_values if not self._is_auto_lang(v)]
            self.source_lang["values"] = source_values
            if self.source_lang.get() not in source_values:
                self.source_lang.set(source_values[0] if source_values else "")
        if hasattr(self, "translation_engine"):
            self.translation_engine["values"] = self._get_engine_labels()
            self.translation_engine_var.set(self._label_for_engine(self.translation_engine_key))
        if hasattr(self, "target_lang"):
            self.target_lang['values'] = self.translations[self.current_language.get()]["target_lang_options"]
            if self.target_lang.get() not in self.target_lang['values']:
                self.target_lang.set(self.target_lang['values'][0])
        self._save_config()

    def on_translation_engine_changed(self, event=None):
        label = (self.translation_engine_var.get() or "").strip()
        self.translation_engine_key = self._resolve_engine_key(label)
        logger.debug("Translation engine changed label=%s key=%s", label, self.translation_engine_key)
        self.toggle_translation_engine_options()
        self._save_config()

    def toggle_translation_engine_options(self):
        if hasattr(self, "enable_translation_var") and not self.enable_translation_var.get():
            if hasattr(self, "model_combo"):
                self.model_combo.configure(state="disabled")
            if hasattr(self, "use_alt_prompt_check"):
                self.use_alt_prompt_check.configure(state="disabled")
            if hasattr(self, "source_lang"):
                self.source_lang.configure(state="disabled")
            return

        is_free = self.translation_engine_key == "libretranslate"
        if hasattr(self, "model_combo"):
            self.model_combo.configure(state="disabled" if is_free else "normal")
        if hasattr(self, "use_alt_prompt_check"):
            self.use_alt_prompt_check.configure(state="disabled" if is_free else "normal")
        if hasattr(self, "source_lang"):
            source_values = self.translations[self.current_language.get()]["source_lang_options"]
            if is_free:
                source_values = [v for v in source_values if not self._is_auto_lang(v)]
            self.source_lang["values"] = source_values
            if self.source_lang.get() not in source_values:
                self.source_lang.set(source_values[0] if source_values else "")
            self.source_lang.configure(state="normal")

    def _validate_translation_settings(self) -> bool:
        if self.translation_engine_key != "libretranslate":
            return True
        source = (self.source_lang.get() or "").strip()
        if not source or self._is_auto_lang(source):
            messagebox.showwarning("提示", self.get_text("fixed_lang_required"))
            return False
        return True

    def create_widgets(self):
        # 頂部控制框架（語言切換）
        top_frame = ttk.Frame(self)
        top_frame.pack(pady=10)

        # 語言切換按鈕
        self.lang_button = ttk.Button(
            top_frame,
            text=self.get_text("switch_language"),
            command=self.switch_language
        )
        self.lang_button.pack(padx=5)

        content_frame = ttk.Frame(self)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        content_frame.columnconfigure(0, weight=1, uniform="columns")
        content_frame.columnconfigure(1, weight=1, uniform="columns")
        content_frame.rowconfigure(0, weight=1)
        self._create_single_page(content_frame)

        # 進度條框架（標籤頁外）
        progress_frame = ttk.Frame(self)
        progress_frame.pack(fill=tk.X, padx=20, pady=10)

        # 進度條
        self.progress_bar = ttk.Progressbar(progress_frame, length=400, mode='determinate')
        self.progress_bar.pack(fill=tk.X)

        # 狀態標籤框架
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        # 狀態標籤
        self.status_label = ttk.Label(status_frame, text="", wraplength=900, justify="center")
        self.status_label.pack(fill=tk.BOTH, expand=True)

    def _create_single_page(self, parent):
        left_frame = ttk.Frame(parent)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        right_frame = ttk.Frame(parent)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        right_frame.columnconfigure(0, weight=1)

        sources_frame = ttk.LabelFrame(left_frame, text=self.get_text("sources_section"))
        sources_frame.pack(fill=tk.X, padx=10, pady=5)

        url_frame = ttk.Frame(sources_frame)
        url_frame.pack(fill=tk.X, padx=10, pady=5)

        self.youtube_urls_label = ttk.Label(url_frame, text=self.get_text("youtube_urls"))
        self.youtube_urls_label.pack(anchor="w")

        self.url_text = tk.Text(url_frame, height=4)
        self.url_text.pack(fill=tk.X, pady=2)

        source_buttons = ttk.Frame(sources_frame)
        source_buttons.pack(fill=tk.X, padx=10, pady=5)

        self.add_urls_button = ttk.Button(
            source_buttons,
            text=self.get_text("add_urls_to_queue"),
            command=self.add_urls_to_queue,
        )
        self.add_urls_button.pack(side=tk.LEFT, padx=5)

        self.select_audio_button = ttk.Button(
            source_buttons,
            text=self.get_text("select_audio_files"),
            command=self.select_audio_files,
        )
        self.select_audio_button.pack(side=tk.LEFT, padx=5)

        queue_frame = ttk.LabelFrame(left_frame, text=self.get_text("queue_section"))
        queue_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.queue_list = tk.Listbox(queue_frame, width=70, height=6, selectmode=tk.SINGLE)
        self.queue_list.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        queue_buttons = ttk.Frame(queue_frame)
        queue_buttons.pack(fill=tk.X, padx=10, pady=5)

        self.clear_queue_button = ttk.Button(
            queue_buttons,
            text=self.get_text("clear_queue"),
            command=self.clear_queue,
        )
        self.clear_queue_button.pack(side=tk.LEFT, padx=5)

        asr_frame = ttk.LabelFrame(right_frame, text=self.get_text("asr_section"))
        asr_frame.pack(fill=tk.X, padx=10, pady=5)

        self._create_asr_settings(asr_frame)

        translation_frame = ttk.LabelFrame(right_frame, text=self.get_text("translation_section"))
        translation_frame.pack(fill=tk.X, padx=10, pady=5)

        self.enable_translation_var = tk.BooleanVar(value=False)
        self.enable_translation_check = ttk.Checkbutton(
            translation_frame,
            text=self.get_text("enable_translation"),
            variable=self.enable_translation_var,
            command=self.toggle_translation_options,
        )
        self.enable_translation_check.pack(anchor="w", padx=10, pady=5)

        self.translation_options_frame = ttk.Frame(translation_frame)
        self.translation_options_frame.pack(fill=tk.X, padx=10, pady=5)
        self._create_translation_settings(self.translation_options_frame)

        output_frame = ttk.LabelFrame(right_frame, text=self.get_text("output_section"))
        output_frame.pack(fill=tk.X, padx=10, pady=5)

        self._create_output_settings(output_frame)

        control_frame = ttk.Frame(right_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)

        self.start_queue_button = ttk.Button(
            control_frame,
            text=self.get_text("start_queue"),
            command=self.start_queue,
        )
        self.start_queue_button.pack(side=tk.LEFT, padx=5)

        self.stop_queue_button = ttk.Button(
            control_frame,
            text=self.get_text("stop_queue"),
            command=self.stop_queue,
        )
        self.stop_queue_button.pack(side=tk.LEFT, padx=5)

        self.toggle_translation_options()
        self.toggle_translation_engine_options()

    def _create_asr_settings(self, parent):
        asr_model_frame = ttk.LabelFrame(parent, text="Whisper 模型設定")
        asr_model_frame.pack(pady=5, padx=10, fill=tk.X)

        model_path_frame = ttk.Frame(asr_model_frame)
        model_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_model_label = ttk.Label(model_path_frame, text=self.get_text("whisper_model_label"))
        self.asr_model_label.pack(side=tk.LEFT, padx=5)

        self.asr_model_path = ttk.Entry(model_path_frame)
        self.asr_model_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_model_path.insert(0, "whisper.cpp/models/ggml-base.bin")
        self.asr_model_path.bind("<FocusOut>", lambda _e: self._save_config())

        self.browse_model_button = ttk.Button(
            model_path_frame,
            text="瀏覽",
            command=self.browse_model
        )
        self.browse_model_button.pack(side=tk.LEFT, padx=5)

        gpu_frame = ttk.Frame(asr_model_frame)
        gpu_frame.pack(fill=tk.X, padx=5, pady=5)

        self.use_gpu_var = tk.BooleanVar(value=True)
        self.use_gpu_check = ttk.Checkbutton(
            gpu_frame,
            text=self.get_text("use_gpu"),
            variable=self.use_gpu_var
        )
        self.use_gpu_check.pack(side=tk.LEFT, padx=5)

        self.gpu_backend_label = ttk.Label(gpu_frame, text=self.get_text("gpu_backend"))
        self.gpu_backend_label.pack(side=tk.LEFT, padx=5)

        self.gpu_backend = ttk.Combobox(
            gpu_frame,
            values=self.translations[self.current_language.get()]["gpu_backend_options"]
        )
        self.gpu_backend.set("auto")
        self.gpu_backend.pack(side=tk.LEFT, padx=5)
        self.gpu_backend.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        transcribe_frame = ttk.LabelFrame(parent, text="轉錄設定")
        transcribe_frame.pack(pady=5, padx=10, fill=tk.X)

        lang_select_frame = ttk.Frame(transcribe_frame)
        lang_select_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_lang_label = ttk.Label(lang_select_frame, text=self.get_text("asr_language_label"))
        self.asr_lang_label.pack(side=tk.LEFT, padx=5)

        self.asr_lang = ttk.Combobox(
            lang_select_frame,
            values=self.translations[self.current_language.get()]["asr_language_options"]
        )
        self.asr_lang.set(self.translations[self.current_language.get()]["asr_language_options"][0])
        self.asr_lang.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_lang.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        output_format_frame = ttk.Frame(transcribe_frame)
        output_format_frame.pack(fill=tk.X, padx=5, pady=5)

        self.output_format_label = ttk.Label(output_format_frame, text=self.get_text("output_format"))
        self.output_format_label.pack(side=tk.LEFT, padx=5)

        self.output_format = ttk.Combobox(
            output_format_frame,
            values=self.translations[self.current_language.get()]["output_format_options"]
        )
        self.output_format.set("srt")
        self.output_format.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.output_format.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

    def _create_translation_settings(self, parent):
        lang_frame = ttk.Frame(parent)
        lang_frame.pack(pady=5, fill=tk.X)

        self.source_lang_label = ttk.Label(lang_frame, text=self.get_text("source_lang_label"))
        self.source_lang_label.grid(row=0, column=0, padx=5)
        self.source_lang = ttk.Combobox(
            lang_frame,
            values=self.translations[self.current_language.get()]["source_lang_options"]
        )
        self.source_lang.set(self._default_source_lang())
        self.source_lang.grid(row=0, column=1, padx=5)
        self.source_lang.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        self.target_lang_label = ttk.Label(lang_frame, text=self.get_text("target_lang_label"))
        self.target_lang_label.grid(row=0, column=2, padx=5)
        self.target_lang = ttk.Combobox(
            lang_frame,
            values=self.translations[self.current_language.get()]["target_lang_options"]
        )
        self.target_lang.set(self.translations[self.current_language.get()]["target_lang_options"][0])
        self.target_lang.grid(row=0, column=3, padx=5)
        self.target_lang.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        engine_frame = ttk.Frame(parent)
        engine_frame.pack(pady=5, fill=tk.X)

        self.translation_engine_label = ttk.Label(engine_frame, text=self.get_text("translation_engine_label"))
        self.translation_engine_label.grid(row=0, column=0, padx=5)
        self.translation_engine = ttk.Combobox(
            engine_frame,
            textvariable=self.translation_engine_var,
            values=self._get_engine_labels(),
            state="readonly",
        )
        self.translation_engine_var.set(self._label_for_engine(self.translation_engine_key))
        self.translation_engine.grid(row=0, column=1, padx=5)
        self.translation_engine.bind("<<ComboboxSelected>>", self.on_translation_engine_changed)

        self.openai_endpoint_label = ttk.Label(engine_frame, text=self.get_text("openai_endpoint_label"))
        self.openai_endpoint_label.grid(row=0, column=2, padx=5)
        self.openai_endpoint = ttk.Entry(engine_frame, width=36)
        self.openai_endpoint.grid(row=0, column=3, padx=5, sticky="ew")
        self.openai_endpoint.insert(0, "")
        self.openai_endpoint.bind("<FocusOut>", lambda _e: self._save_config())
        engine_frame.columnconfigure(3, weight=1)

        model_frame = ttk.Frame(parent)
        model_frame.pack(pady=5, fill=tk.X)

        self.model_label = ttk.Label(model_frame, text=self.get_text("model_label"))
        self.model_label.grid(row=0, column=0, padx=5)
        self.model_combo = ttk.Combobox(model_frame, values=self.get_model_list())
        self.model_combo.set("gpt-oss:20b")
        self.model_combo.grid(row=0, column=1, padx=5)
        self.model_combo.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        self.parallel_label = ttk.Label(model_frame, text=self.get_text("parallel_label"))
        self.parallel_label.grid(row=0, column=2, padx=5)
        self.parallel_requests = ttk.Combobox(
            model_frame,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20"]
        )
        self.parallel_requests.set("10")
        self.parallel_requests.grid(row=0, column=3, padx=5)
        self.parallel_requests.bind("<<ComboboxSelected>>", lambda _e: self._save_config())

        checkbox_frame = ttk.Frame(parent)
        checkbox_frame.pack(pady=5, fill=tk.X)

        self.replace_original_check = ttk.Checkbutton(
            checkbox_frame,
            text=self.get_text("replace_original"),
            variable=self.replace_original_var
        )
        self.replace_original_check.pack(side=tk.LEFT, padx=5)

        self.use_alt_prompt_check = ttk.Checkbutton(
            checkbox_frame,
            text="使用替代提示詞",
            variable=self.use_alt_prompt_var
        )
        self.use_alt_prompt_check.pack(side=tk.LEFT, padx=5)

    def _create_output_settings(self, parent):
        output_path_frame = ttk.Frame(parent)
        output_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_output_path_label = ttk.Label(output_path_frame, text="輸出資料夾：")
        self.asr_output_path_label.pack(side=tk.LEFT, padx=5)

        self.asr_output_path = ttk.Entry(output_path_frame)
        self.asr_output_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_output_path.insert(0, "transcriptions")
        self.asr_output_path.bind("<FocusOut>", lambda _e: self._save_config())

        self.browse_output_button = ttk.Button(
            output_path_frame,
            text="瀏覽",
            command=self.browse_output_dir
        )
        self.browse_output_button.pack(side=tk.LEFT, padx=5)

        self.open_output_button = ttk.Button(
            output_path_frame,
            text=self.get_text("open_output_folder"),
            command=self.open_output_dir,
        )
        self.open_output_button.pack(side=tk.LEFT, padx=5)

        output_option_frame = ttk.Frame(parent)
        output_option_frame.pack(fill=tk.X, padx=5, pady=5)

        self.output_to_source_check = ttk.Checkbutton(
            output_option_frame,
            text=self.get_text("output_to_source"),
            variable=self.output_to_source_var,
        )
        self.output_to_source_check.pack(side=tk.LEFT, padx=5)

    def toggle_translation_options(self):
        state = "normal" if self.enable_translation_var.get() else "disabled"
        for child in self.translation_options_frame.winfo_children():
            self._set_widget_state(child, state)
        if state == "normal":
            self.toggle_translation_engine_options()
        self._save_config()

    def _set_widget_state(self, widget, state):
        try:
            widget.configure(state=state)
        except tk.TclError:
            pass
        for child in getattr(widget, "winfo_children", lambda: [])():
            self._set_widget_state(child, state)

    def _create_translate_tab(self):
        """創建翻譯標籤頁內容"""
        # 按鈕框架
        button_frame = ttk.Frame(self.translate_tab)
        button_frame.pack(pady=10)

        # 檔案選擇按鈕
        self.file_button = ttk.Button(
            button_frame,
            text=self.get_text("select_files"),
            command=self.select_files
        )
        self.file_button.pack(side=tk.LEFT, padx=5)

        # 文件夾批量新增按鈕
        self.folder_button = ttk.Button(
            button_frame,
            text=self.get_text("select_folder"),
            command=self.select_folder
        )
        self.folder_button.pack(side=tk.LEFT, padx=5)

        # 檔案列表框架
        list_frame = ttk.Frame(self.translate_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 檔案列表
        self.file_list = tk.Listbox(list_frame, width=70, height=10, selectmode=tk.SINGLE)
        self.file_list.pack(fill=tk.BOTH, expand=True)

        # 綁定 Del 鍵事件
        self.file_list.bind('<Delete>', self.delete_selected_file)

        # 添加滾動條
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.file_list.configure(yscrollcommand=scrollbar.set)

        # 語言選擇框架
        lang_frame = ttk.Frame(self.translate_tab)
        lang_frame.pack(pady=10)

        # 原文語言標籤和選擇框
        self.source_lang_label = ttk.Label(lang_frame, text=self.get_text("source_lang_label"))
        self.source_lang_label.grid(row=0, column=0)
        self.source_lang = ttk.Combobox(lang_frame, values=self.translations[self.current_language.get()]["source_lang_options"])
        self.source_lang.set(self.translations[self.current_language.get()]["source_lang_options"][0])
        self.source_lang.grid(row=0, column=1)

        # 目標語言標籤和選擇框
        self.target_lang_label = ttk.Label(lang_frame, text=self.get_text("target_lang_label"))
        self.target_lang_label.grid(row=0, column=2)
        self.target_lang = ttk.Combobox(lang_frame, values=self.translations[self.current_language.get()]["target_lang_options"])
        self.target_lang.set(self.translations[self.current_language.get()]["target_lang_options"][0])
        self.target_lang.grid(row=0, column=3)

        # 模型選擇框架
        model_frame = ttk.Frame(self.translate_tab)
        model_frame.pack(pady=10)

        # 模型選擇標籤和選擇框
        self.model_label = ttk.Label(model_frame, text=self.get_text("model_label"))
        self.model_label.grid(row=0, column=0)
        self.model_combo = ttk.Combobox(model_frame, values=self.get_model_list())
        self.model_combo.set("gpt-oss:20b")
        self.model_combo.grid(row=0, column=1)

        # 並行請求數標籤和選擇框
        self.parallel_label = ttk.Label(model_frame, text=self.get_text("parallel_label"))
        self.parallel_label.grid(row=0, column=2)
        self.parallel_requests = ttk.Combobox(model_frame, values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20"])
        self.parallel_requests.set("10")
        self.parallel_requests.grid(row=0, column=3)

        # Checkbox 框架
        checkbox_frame = ttk.Frame(self.translate_tab)
        checkbox_frame.pack(pady=5)

        # 清理模式複選框
        self.clean_mode_check = ttk.Checkbutton(
            checkbox_frame,
            text=self.get_text("auto_clean"),
            variable=self.clean_mode_var
        )
        self.clean_mode_check.grid(row=0, column=0, padx=10, pady=2, sticky='w')

        # 調試模式複選框
        self.debug_mode_check = ttk.Checkbutton(
            checkbox_frame,
            text=self.get_text("debug_mode"),
            variable=self.debug_mode_var
        )
        self.debug_mode_check.grid(row=0, column=1, padx=10, pady=2, sticky='w')

        # 自動清理工作區複選框
        self.auto_clean_workspace_check = ttk.Checkbutton(
            checkbox_frame,
            text=self.get_text("clean_workspace"),
            variable=self.auto_clean_workspace_var
        )
        self.auto_clean_workspace_check.grid(row=1, column=0, padx=10, pady=2, sticky='w')

        # 取代原始檔案複選框
        self.replace_original_check = ttk.Checkbutton(
            checkbox_frame,
            text=self.get_text("replace_original"),
            variable=self.replace_original_var
        )
        self.replace_original_check.grid(row=1, column=1, padx=10, pady=2, sticky='w')

        # 使用替代提示詞複選框
        self.use_alt_prompt_check = ttk.Checkbutton(
            checkbox_frame,
            text="使用替代提示詞",
            variable=self.use_alt_prompt_var
        )
        self.use_alt_prompt_check.grid(row=2, column=0, padx=10, pady=2, sticky='w')

        # 配置 grid
        checkbox_frame.grid_columnconfigure(0, weight=1)
        checkbox_frame.grid_columnconfigure(1, weight=1)

        # 翻譯按鈕
        self.translate_button = ttk.Button(
            self.translate_tab,
            text=self.get_text("start_translation"),
            command=self.start_translation
        )
        self.translate_button.pack(pady=10)

    def _create_asr_tab(self):
        """創建 ASR 標籤頁內容"""
        # 按鈕框架
        button_frame = ttk.Frame(self.asr_tab)
        button_frame.pack(pady=10)

        # 選擇音訊檔案按鈕
        self.audio_button = ttk.Button(
            button_frame,
            text=self.get_text("select_audio"),
            command=self.select_audio
        )
        self.audio_button.pack(side=tk.LEFT, padx=5)

        # YouTube URL 框架
        youtube_frame = ttk.Frame(self.asr_tab)
        youtube_frame.pack(pady=5, padx=10, fill=tk.X)

        self.youtube_url_label = ttk.Label(youtube_frame, text=self.get_text("youtube_url"))
        self.youtube_url_label.pack(anchor='w')

        self.youtube_url_entry = ttk.Entry(youtube_frame)
        self.youtube_url_entry.pack(fill=tk.X, pady=2)

        # 從 YouTube 下載按鈕
        self.youtube_button = ttk.Button(
            youtube_frame,
            text=self.get_text("download_from_youtube"),
            command=self.download_from_youtube
        )
        self.youtube_button.pack(anchor='e', pady=2)

        # 音訊檔案路徑顯示
        self.audio_path_label = ttk.Label(self.asr_tab, text="選擇的檔案：無")
        self.audio_path_label.pack(pady=5, padx=10, anchor='w')

        # 模型設定框架
        asr_model_frame = ttk.LabelFrame(self.asr_tab, text="Whisper 模型設定")
        asr_model_frame.pack(pady=10, padx=10, fill=tk.X)

        # Whisper 模型路徑
        model_path_frame = ttk.Frame(asr_model_frame)
        model_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_model_label = ttk.Label(model_path_frame, text=self.get_text("whisper_model_label"))
        self.asr_model_label.pack(side=tk.LEFT, padx=5)

        self.asr_model_path = ttk.Entry(model_path_frame)
        self.asr_model_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_model_path.insert(0, "whisper.cpp/models/ggml-base.bin")

        # 模型選擇按鈕
        self.browse_model_button = ttk.Button(
            model_path_frame,
            text="瀏覽",
            command=self.browse_model
        )
        self.browse_model_button.pack(side=tk.LEFT, padx=5)

        # GPU 設定
        gpu_frame = ttk.Frame(asr_model_frame)
        gpu_frame.pack(fill=tk.X, padx=5, pady=5)

        self.use_gpu_var = tk.BooleanVar(value=True)
        self.use_gpu_check = ttk.Checkbutton(
            gpu_frame,
            text=self.get_text("use_gpu"),
            variable=self.use_gpu_var
        )
        self.use_gpu_check.pack(side=tk.LEFT, padx=5)

        self.gpu_backend_label = ttk.Label(gpu_frame, text=self.get_text("gpu_backend"))
        self.gpu_backend_label.pack(side=tk.LEFT, padx=5)

        self.gpu_backend = ttk.Combobox(
            gpu_frame,
            values=self.translations[self.current_language.get()]["gpu_backend_options"]
        )
        self.gpu_backend.set("auto")
        self.gpu_backend.pack(side=tk.LEFT, padx=5)

        # 轉錄設定框架
        transcribe_frame = ttk.LabelFrame(self.asr_tab, text="轉錄設定")
        transcribe_frame.pack(pady=10, padx=10, fill=tk.X)

        # 語言選擇
        lang_select_frame = ttk.Frame(transcribe_frame)
        lang_select_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_lang_label = ttk.Label(lang_select_frame, text=self.get_text("asr_language_label"))
        self.asr_lang_label.pack(side=tk.LEFT, padx=5)

        self.asr_lang = ttk.Combobox(
            lang_select_frame,
            values=self.translations[self.current_language.get()]["asr_language_options"]
        )
        self.asr_lang.set(self.translations[self.current_language.get()]["asr_language_options"][0])
        self.asr_lang.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 輸出格式選擇
        output_format_frame = ttk.Frame(transcribe_frame)
        output_format_frame.pack(fill=tk.X, padx=5, pady=5)

        self.output_format_label = ttk.Label(output_format_frame, text=self.get_text("output_format"))
        self.output_format_label.pack(side=tk.LEFT, padx=5)

        self.output_format = ttk.Combobox(
            output_format_frame,
            values=self.translations[self.current_language.get()]["output_format_options"]
        )
        self.output_format.set("srt")
        self.output_format.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        # 輸出路徑
        output_path_frame = ttk.Frame(transcribe_frame)
        output_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_output_path_label = ttk.Label(output_path_frame, text="輸出檔案：")
        self.asr_output_path_label.pack(side=tk.LEFT, padx=5)

        self.asr_output_path = ttk.Entry(output_path_frame)
        self.asr_output_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_output_path.insert(0, "transcription.srt")

        # 開始轉錄按鈕
        self.asr_button = ttk.Button(
            self.asr_tab,
            text=self.get_text("start_asr"),
            command=self.start_asr
        )
        self.asr_button.pack(pady=10)

    def handle_drop(self, event):
        """處理檔案拖放"""
        files = self.tk.splitlist(event.data)
        logger.debug("Handle drop received count=%s", len(files))
        added = 0
        skipped = 0
        for file in files:
            # 檢查是否為 .srt 檔案
            if file.lower().endswith('.srt'):
                # 在 Windows 上移除檔案路徑的大括號（如果有的話）
                file = file.strip('{}')
                self.file_list.insert(tk.END, file)
                added += 1
            else:
                skipped += 1
                messagebox.showwarning("警告", f"檔案 {file} 不是 SRT 格式，已略過")
        logger.debug("Handle drop completed added=%s skipped=%s", added, skipped)

    def select_files(self):
        files = filedialog.askopenfilenames(filetypes=[("SRT files", "*.srt")])
        logger.debug("File picker selected count=%s", len(files))
        for file in files:
            self.file_list.insert(tk.END, file)

    def add_urls_to_queue(self):
        logger.debug("Add URLs to queue requested")
        urls = self.url_text.get("1.0", tk.END)
        url_list = _parse_urls(urls)
        logger.debug("Parsed URLs count=%s", len(url_list))
        for line in url_list:
            item = {"kind": "url", "value": line}
            with self.queue_items_lock:
                self.queue_items.append(item)
            self.queue_list.insert(tk.END, _queue_item_label(item))
            logger.debug("URL added to queue: %s", line)
        self.url_text.delete("1.0", tk.END)
        logger.info("URLs added to queue count=%s", len(url_list))

    def select_audio_files(self):
        file_paths = filedialog.askopenfilenames(
            title="選擇音訊檔案",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.m4a *.flac *.ogg *.wma"),
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.wmv *.mpeg *.mpg"),
                ("All files", "*.*")
            ]
        )
        if not file_paths:
            logger.debug("Audio file selection cancelled")
            return
        for path in file_paths:
            item = {"kind": "file", "value": path}
            with self.queue_items_lock:
                self.queue_items.append(item)
            self.queue_list.insert(tk.END, _queue_item_label(item))
            logger.debug("Audio file added to queue: %s", path)
        logger.debug("Audio files selected count=%s", len(file_paths))

    def clear_queue(self):
        self.queue_list.delete(0, tk.END)
        with self.queue_items_lock:
            self.queue_items = []
        self.queue_total = 0
        logger.debug("Queue cleared")

    def start_queue(self):
        logger.info("Start queue requested")
        if self.is_running:
            logger.warning("Queue already running, ignoring start request")
            return
        if _should_translate(self.enable_translation_var.get()):
            if not self._validate_translation_settings():
                return
        if self.url_text.get("1.0", tk.END).strip():
            logger.debug("Adding pending URLs before starting queue")
            self.add_urls_to_queue()
        with self.queue_items_lock:
            if not self.queue_items:
                logger.warning("Queue is empty, cannot start")
                messagebox.showwarning("提示", "請先加入待處理項目")
                return
            self.queue_total = len(self.queue_items)
        logger.info("Starting queue processing total_items=%s", self.queue_total)
        self.is_running = True
        self._process_next_queue_item()

    def stop_queue(self):
        logger.info("Stop queue requested")
        self.is_running = False

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="選擇輸出資料夾")
        if directory:
            self.asr_output_path.delete(0, tk.END)
            self.asr_output_path.insert(0, directory)
            self._save_config()

    def open_output_dir(self):
        output_dir = (self.asr_output_path.get() or "").strip() or "transcriptions"
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        try:
            if sys.platform.startswith("darwin"):
                subprocess.run(["open", output_dir], check=False)
            elif os.name == "nt":
                os.startfile(output_dir)  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", output_dir], check=False)
            logger.debug("Opened output directory: %s", output_dir)
        except Exception as exc:
            logger.warning("Failed to open output directory: %s error=%s", output_dir, exc)
            messagebox.showerror(self.get_text("error"), f"無法開啟資料夾：{output_dir}")
            logger.debug("Output directory selected: %s", directory)

    def _process_next_queue_item(self):
        if not self.is_running:
            logger.debug("Queue processing stopped by user")
            return
        with self.queue_items_lock:
            item = _pop_next_queue_item(self.queue_items)
            if item is None:
                self.is_running = False
                self.status_label.config(text="佇列完成")
                logger.info("Queue processing completed")
                return
            current_index = self.queue_total - len(self.queue_items)
            remaining = len(self.queue_items)
        logger.debug("Processing queue item index=%s/%s remaining=%s kind=%s",
                     current_index, self.queue_total, remaining, item.get("kind"))
        self.status_label.config(text=_queue_status_text(current_index, self.queue_total, "處理中"))
        self._run_queue_item(item, current_index)

    def _run_queue_item(self, item, index):
        def _run():
            try:
                logger.debug("Queue item execution started index=%s kind=%s", index, item["kind"])
                if item["kind"] == "url":
                    logger.info("Downloading audio from URL: %s", item["value"])
                    from src.asr.audio_downloader import AudioDownloader
                    downloader = AudioDownloader(output_dir="downloads")
                    audio_path = downloader.download_audio_to_wav(item["value"])
                    logger.info("Audio downloaded successfully: %s", audio_path)
                else:
                    audio_path = item["value"]
                    logger.debug("Using local audio file: %s", audio_path)

                if not audio_path or not os.path.exists(audio_path):
                    logger.error("Audio file not found: %s", audio_path)
                    raise FileNotFoundError(f"音訊檔案不存在：{audio_path}")

                prefer_source_dir = item.get("kind") == "file"
                output_path = self._resolve_asr_output_path(audio_path, prefer_source_dir=prefer_source_dir)
                logger.debug("ASR output path resolved: %s", output_path)
                self._run_asr_request(audio_path, output_path)
                logger.info("ASR completed for index=%s output=%s", index, output_path)

                if _should_translate(self.enable_translation_var.get()):
                    logger.debug("Translation enabled, starting translation for: %s", output_path)
                    self._run_translation_for_output(output_path, index)
                else:
                    logger.debug("Translation disabled, skipping")

                self.after(0, lambda: self._on_queue_item_done(index, True, output_path))
            except Exception as exc:
                logger.error("Queue item failed index=%s error=%s", index, exc)
                error_msg = str(exc)
                self.after(0, lambda msg=error_msg: self._on_queue_item_done(index, False, msg))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _run_asr_request(self, audio_path, output_path):
        if not self.asr_coordinator:
            raise RuntimeError(self.get_text("asr_not_available"))

        from src.application.asr_coordinator import ASRRequest

        language = self._resolve_asr_language()

        request = ASRRequest(
            input_path=audio_path,
            output_path=output_path,
            model_path=self.asr_model_path.get(),
            language=language,
            use_gpu=self.use_gpu_var.get(),
            gpu_backend=self.gpu_backend.get(),
            n_threads=4,
            output_format=self.output_format.get(),
            max_retries=1
        )
        self.asr_coordinator.run(request)

    def _resolve_asr_output_path(self, audio_path, prefer_source_dir: bool = True):
        output_dir = self.asr_output_path.get().strip() or "transcriptions"
        if self.output_to_source_var.get() and prefer_source_dir and audio_path:
            source_dir = os.path.dirname(os.path.abspath(audio_path))
            if source_dir:
                output_dir = source_dir

        os.makedirs(output_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(audio_path))[0]
        ext = self.output_format.get()
        return os.path.join(output_dir, f"{base_name}.{ext}")

    def _run_translation_for_output(self, output_path, index):
        if not output_path.lower().endswith(".srt"):
            logger.warning("Translation skipped (non-srt) path=%s", output_path)
            return
        self.after(
            0,
            lambda: self.status_label.config(
                text=_queue_status_text(index, self.queue_total, "翻譯中")
            )
        )
        translation_client = self.free_translation_client if self.translation_engine_key == "libretranslate" else None
        thread = TranslationThread(
            output_path,
            self.source_lang.get(),
            self.target_lang.get(),
            self.model_combo.get(),
            self.parallel_requests.get(),
            self.update_progress,
            self.file_translated,
            self.debug_mode_var.get(),
            self.replace_original_var.get(),
            self.use_alt_prompt_var.get(),
            translation_client=translation_client,
        )
        thread.set_app(self)
        thread.start()
        # Don't join() - it blocks the UI thread. The thread will call back via file_translated()

    def _on_queue_item_done(self, index, success, message):
        if success:
            self.status_label.config(text=_queue_status_text(index, self.queue_total, "完成"))
        else:
            self.status_label.config(
                text=f"{_queue_status_text(index, self.queue_total, '失敗')}: {message}"
            )

        if self.is_running:
            self._process_next_queue_item()

    # ========== ASR Methods ==========
    def select_audio(self):
        """選擇音訊檔案"""
        file_path = filedialog.askopenfilename(
            title="選擇音訊檔案",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.m4a *.flac *.ogg *.wma"),
                ("Video files", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.wmv *.mpeg *.mpg"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.audio_path_label.config(text=f"選擇的檔案：{file_path}")
            logger.debug("Audio file selected: %s", file_path)

    def browse_model(self):
        """瀏覽 Whisper 模型檔案"""
        file_path = filedialog.askopenfilename(
            title="選擇 Whisper 模型",
            filetypes=[("Model files", "*.bin"), ("All files", "*.*")]
        )
        if file_path:
            self.asr_model_path.delete(0, tk.END)
            self.asr_model_path.insert(0, file_path)
            logger.debug("Whisper model selected: %s", file_path)
            self._save_config()

    def download_from_youtube(self):
        """從 YouTube 下載音訊"""
        url = self.youtube_url_entry.get().strip()
        if not url:
            messagebox.showwarning("警告", "請輸入 YouTube URL")
            return

        self.status_label.config(text="正在從 YouTube 下載音訊...")

        def download_thread():
            """Download audio in background thread."""
            try:
                from src.asr.audio_downloader import AudioDownloader

                downloader = AudioDownloader(output_dir="downloads")
                audio_path = downloader.download_audio_to_wav(url)

                # Update UI from main thread
                def update_success():
                    self.audio_path_label.config(text=f"選擇的檔案：{audio_path}")
                    self.status_label.config(text="下載完成！")
                    logger.info("Audio downloaded from YouTube: %s", audio_path)

                def update_error(error_msg):
                    messagebox.showerror("錯誤", "下載失敗")
                    self.status_label.config(text="下載失敗")
                    logger.error("YouTube download error: %s", error_msg)

                if audio_path:
                    self.after(0, update_success)
                else:
                    self.after(0, lambda: update_error("下載失敗"))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: self._show_download_error(error_msg))

        def _show_download_error(self, error_msg):
            """Show download error in main thread."""
            messagebox.showerror("錯誤", f"下載失敗：{error_msg}")
            self.status_label.config(text="下載失敗")
            logger.error("YouTube download error: %s", error_msg)

        # Start download in background thread
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def start_asr(self):
        """開始 ASR 轉錄"""
        # 檢查音訊檔案
        audio_text = self.audio_path_label.cget("text")
        if "無" in audio_text or not audio_text:
            messagebox.showwarning("警告", "請先選擇或下載音訊檔案")
            return

        # 提取音訊檔案路徑
        audio_path = audio_text.replace("選擇的檔案：", "")
        if not os.path.exists(audio_path):
            messagebox.showerror("錯誤", f"音訊檔案不存在：{audio_path}")
            return

        # 檢查模型路徑
        model_path = self.asr_model_path.get()
        if not os.path.exists(model_path):
            messagebox.showerror("錯誤", f"模型檔案不存在：{model_path}")
            return

        # 獲取設定
        use_gpu = self.use_gpu_var.get()
        gpu_backend = self.gpu_backend.get()
        language = self._resolve_asr_language()
        output_format = self.output_format.get()
        output_path = self.asr_output_path.get()

        # 建立請求
        from src.application.asr_coordinator import ASRRequest

        request = ASRRequest(
            input_path=audio_path,
            output_path=output_path,
            model_path=model_path,
            language=language,
            use_gpu=use_gpu,
            gpu_backend=gpu_backend,
            n_threads=4,
            output_format=output_format,
            max_retries=1
        )

        # 執行轉錄
        self.status_label.config(text="正在轉錄...")

        def run_asr():
            try:
                summary = self.asr_coordinator.run(request)
                if summary.successful_files > 0:
                    self.after(0, lambda: messagebox.showinfo("成功", f"轉錄完成！\n輸出：{output_path}"))
                    self.after(0, lambda: self.status_label.config(text="轉錄完成！"))
                else:
                    self.after(0, lambda: messagebox.showerror("錯誤", "轉錄失敗"))
                    self.after(0, lambda: self.status_label.config(text="轉錄失敗"))
            except Exception as e:
                logger.error("ASR error: %s", e)
                self.after(0, lambda: messagebox.showerror("錯誤", f"轉錄失敗：{e}"))
                self.after(0, lambda: self.status_label.config(text="轉錄失敗"))

        import threading
        thread = threading.Thread(target=run_asr, daemon=True)
        thread.start()
    # ========== End ASR Methods ==========

    def select_folder(self):
        """選擇文件夾並批量添加 SRT 檔案"""
        folder_path = filedialog.askdirectory(title="選擇包含 SRT 檔案的文件夾")
        if not folder_path:
            logger.debug("Folder selection cancelled")
            return
        logger.debug("Folder selection started path=%s", folder_path)

        # 計數器
        added_count = 0
        skipped_count = 0
        backup_count = 0

        # Build set of existing paths for O(1) lookup
        existing_paths = set()
        for i in range(self.file_list.size()):
            existing_paths.add(self.file_list.get(i))

        # 遍歷文件夾中的所有檔案
        for root, dirs, files in os.walk(folder_path):
            # 跳過 backup 目錄
            if 'backup' in dirs:
                dirs.remove('backup')  # 這會讓 os.walk 跳過 backup 目錄

            # 檢查當前目錄是否為 backup 目錄
            if os.path.basename(root) == 'backup':
                backup_count += len([f for f in files if f.lower().endswith('.srt')])
                continue

            for file in files:
                if file.lower().endswith('.srt'):
                    # 跳過中文翻譯檔案
                    if file.lower().endswith('.zh_tw.srt'):
                        skipped_count += 1
                        continue

                    full_path = os.path.join(root, file)

                    # 檢查是否已在列表中 (O(1) lookup)
                    if full_path in existing_paths:
                        skipped_count += 1
                        logger.debug("File already in list, skipping: %s", full_path)
                    else:
                        self.file_list.insert(tk.END, full_path)
                        existing_paths.add(full_path)
                        added_count += 1
                        logger.debug("File added to list: %s", full_path)

        # 顯示結果
        message = f"已添加 {added_count} 個 SRT 檔案"
        if skipped_count > 0 or backup_count > 0:
            message += f"\n已跳過 {skipped_count} 個檔案（包含已翻譯檔案或重複檔案）"
            if backup_count > 0:
                message += f"\n已跳過 {backup_count} 個備份目錄中的檔案"
        
        if added_count > 0:
            messagebox.showinfo("完成", message)
        else:
            messagebox.showwarning("提示", "未找到可添加的 SRT 檔案")
        logger.debug(
            "Folder selection completed path=%s added=%s skipped=%s backup_skipped=%s",
            folder_path,
            added_count,
            skipped_count,
            backup_count,
        )

    def get_model_list(self):
        import urllib.request
        import json
        endpoint = os.getenv("OPENAI_COMPAT_ENDPOINT") or os.getenv("OLLAMA_ENDPOINT") or "http://localhost:11434/v1/chat/completions"
        base = endpoint.rstrip("/")
        if base.endswith("/v1/chat/completions"):
            base = base[: -len("/v1/chat/completions")]
        elif base.endswith("/chat/completions"):
            base = base[: -len("/chat/completions")]
        if base.endswith("/v1"):
            url = f"{base}/models"
        else:
            url = f"{base}/v1/models"
        logger.debug("Fetching model list from endpoint=%s", url)
        try:
            with urllib.request.urlopen(url) as response:
                models = json.loads(response.read())
                if 'data' in models and isinstance(models['data'], list):
                    model_ids = [model['id'] for model in models['data']]
                    logger.debug("Fetched model list count=%s", len(model_ids))
                    return model_ids
        except Exception as exc:
            logger.warning("Failed to fetch model list error=%s", exc)
            pass
        return []

    def start_translation(self):
        """開始翻譯"""
        logger.info("Start translation requested files=%s", self.file_list.size())
        if not self.file_list.size():
            logger.warning("Start translation blocked: no files selected")
            messagebox.showwarning(
                self.get_text("no_files"),
                self.get_text("no_files_message")
            )
            return
        if not self._validate_translation_settings():
            return

        # 如果選擇取代原始檔案，詢問使用者確認
        if self.replace_original_var.get():
            if not messagebox.askyesno(
                self.get_text("confirm"),
                self.get_text("replace_warning")
            ):
                logger.debug("Start translation cancelled by replace confirmation dialog")
                return

        # 如果開啟了清理模式，先清理檔案
        if self.clean_mode_var.get():
            logger.debug("Pre-translation cleaning enabled")
            self.status_label.config(text=self.get_text("cleaning"))
            self.update_idletasks()
            
            total_cleaned = 0
            total_subtitles = 0
            
            for i in range(self.file_list.size()):
                input_file = self.file_list.get(i)
                try:
                    # 清理檔案並獲取結果
                    result = clean_srt_file(input_file, self.replace_original_var.get())
                    
                    total_cleaned += result["cleaned"]
                    total_subtitles += result["total"]
                    
                    # 更新進度
                    progress = (i + 1) / self.file_list.size() * 100
                    self.progress_bar['value'] = progress
                    self.status_label.config(
                        text=self.get_text("cleaning_progress").format(
                            i+1,
                            self.file_list.size(),
                            progress,
                            total_cleaned,
                            total_subtitles
                        )
                    )
                    self.update_idletasks()
                    
                except Exception as e:
                    messagebox.showerror(
                        self.get_text("error"),
                        str(e)
                    )
                    return

            self.status_label.config(
                text=self.get_text("cleaning_complete").format(
                    total_cleaned,
                    total_subtitles
                )
            )
            logger.debug(
                "Pre-translation cleaning completed total_cleaned=%s total_subtitles=%s",
                total_cleaned,
                total_subtitles,
            )
            self.update_idletasks()

        # 重置進度條
        self.progress_bar['value'] = 0
        total_files = self.file_list.size()

        if self.coordinator and self.translation_engine_key != "libretranslate":
            from src.application.models import TranslationRequest

            request = TranslationRequest(
                file_paths=[self.file_list.get(i) for i in range(total_files)],
                source_lang=self.source_lang.get(),
                target_lang=self.target_lang.get(),
                model_name=self.model_combo.get(),
                parallel_requests=int(self.parallel_requests.get()),
                clean_before_translate=self.clean_mode_var.get(),
                replace_original=self.replace_original_var.get(),
                use_alt_prompt=self.use_alt_prompt_var.get(),
            )
            logger.info(
                "Dispatching coordinator request files=%s source=%s target=%s model=%s parallel=%s clean=%s replace=%s alt_prompt=%s",
                total_files,
                request.source_lang,
                request.target_lang,
                request.model_name,
                request.parallel_requests,
                request.clean_before_translate,
                request.replace_original,
                request.use_alt_prompt,
            )
            self.coordinator.run_async(request, callback=self._on_coordinator_done)
            self.status_label.config(
                text=self.get_text("translating").format(total_files)
            )
            return
        
        # 開始翻譯
        translation_client = self.free_translation_client if self.translation_engine_key == "libretranslate" else None
        for i in range(total_files):
            file_path = self.file_list.get(i)
            thread = TranslationThread(
                file_path, 
                self.source_lang.get(), 
                self.target_lang.get(), 
                self.model_combo.get(),
                self.parallel_requests.get(),
                self.update_progress,
                self.file_translated,
                self.debug_mode_var.get(),
                self.replace_original_var.get(),
                self.use_alt_prompt_var.get(),
                translation_client=translation_client,
            )
            thread.set_app(self)
            thread.start()
            logger.debug("Started legacy translation thread file=%s", file_path)

        self.status_label.config(
            text=self.get_text("translating").format(total_files)
        )

    def _on_coordinator_done(self, summary):
        self.after(0, lambda: self._on_coordinator_complete(summary))

    def _on_coordinator_complete(self, summary):
        logger.info(
            "Coordinator completed total=%s success=%s failed=%s auto_clean_workspace=%s",
            summary.total_files,
            summary.successful_files,
            summary.failed_files,
            self.auto_clean_workspace_var.get(),
        )
        if self.auto_clean_workspace_var.get():
            self.file_list.delete(0, tk.END)
            self.status_label.config(text=self.get_text("workspace_cleaned"))
            self.progress_bar['value'] = 0
            messagebox.showinfo(
                self.get_text("confirm"),
                self.get_text("workspace_cleaned"),
            )
            return

        self.status_label.config(
            text=f"{self.get_text('all_complete')} (ok={summary.successful_files}, failed={summary.failed_files})"
        )
        self.progress_bar['value'] = 0
        messagebox.showinfo(
            self.get_text("confirm"),
            self.get_text("all_complete"),
        )

    def on_coordinator_event(self, event):
        logger.debug(
            "Coordinator event received current=%s total=%s message=%s",
            getattr(event, "current", None),
            getattr(event, "total", None),
            getattr(event, "message", ""),
        )
        self.after(0, lambda: self._apply_progress(event))

    def on_asr_event(self, event):
        """Handle ASR coordinator events."""
        logger.debug(
            "ASR event received current=%s total=%s message=%s",
            getattr(event, "current", None),
            getattr(event, "total", None),
            getattr(event, "message", ""),
        )
        self.after(0, lambda: self._apply_progress(event))

    def _apply_progress(self, event):
        current = getattr(event, "current", None)
        total = getattr(event, "total", None)
        message = getattr(event, "message", "")
        if current is None or total in (None, 0):
            return

        percentage = int(current / total * 100)
        self.progress_bar["value"] = percentage
        if message:
            self.status_label.config(text=message)
        else:
            self.status_label.config(
                text=self.get_text("translation_progress").format(
                    current,
                    total,
                    percentage,
                )
            )

    def update_progress(self, current, total, extra_data=None):
        """更新進度"""
        if extra_data and extra_data.get("type") == "file_conflict":
            logger.debug("File conflict progress event path=%s", extra_data.get("path"))
            # 在主線程中顯示對話框
            result = self.show_countdown_dialog(
                self.get_text("file_conflict_message").format(os.path.basename(extra_data['path'])),
                countdown=5
            )
            
            # 將結果發送回翻譯線程
            extra_data["queue"].put(result)
            logger.debug("File conflict result sent result=%s", result)
            return
            
        # 正常的進度更新
        if current >= 0 and total >= 0:
            percentage = int(current / total * 100)
            self.progress_bar['value'] = percentage
            self.status_label.config(
                text=self.get_text("translation_progress").format(
                    current,
                    total,
                    percentage
                )
            )
            logger.debug("Progress updated current=%s total=%s percentage=%s", current, total, percentage)
            self.update_idletasks()

    def file_translated(self, message):
        """處理檔案翻譯完成的回調"""
        logger.debug("File translated callback message=%s", message)
        current_text = self.status_label.cget("text")
        self.status_label.config(text=f"{current_text}\n{message}")
        
        # 檢查是否所有檔案都已翻譯完成
        if "翻譯完成" in message:
            # 從檔案列表中移除已翻譯的檔案
            if self.auto_clean_workspace_var.get():
                logger.debug("Auto-cleanup enabled, processing completed file")
                # Extract the output path from message format: "翻譯完成 | 檔案已成功保存為: {path}"
                if "檔案已成功保存為:" in message:
                    completed_path = message.split("檔案已成功保存為:")[-1].strip()
                    completed_basename = os.path.basename(completed_path)
                    logger.debug("Extracted completed file basename=%s", completed_basename)

                    for i in range(self.file_list.size()):
                        file_basename = os.path.basename(self.file_list.get(i))
                        # Exact match to avoid false positives (e.g., "test.srt" vs "contest.srt")
                        if file_basename == completed_basename:
                            logger.info("Removing completed file from list index=%s basename=%s", i, file_basename)
                            self.file_list.delete(i)
                            break
                    else:
                        logger.warning("Completed file not found in list basename=%s", completed_basename)
                else:
                    logger.warning("Cannot extract output path from message: %s", message)
            else:
                logger.debug("Auto-cleanup disabled, keeping file in list")

            # 如果檔案列表為空且啟用了自動清理，顯示完成訊息
            if self.file_list.size() == 0 and self.auto_clean_workspace_var.get():
                logger.info("All files processed, workspace cleaned")
                self.status_label.config(text=self.get_text("workspace_cleaned"))
                self.progress_bar['value'] = 0
                messagebox.showinfo(
                    self.get_text("confirm"),
                    self.get_text("workspace_cleaned")
                )
            # 如果檔案列表不為空或未啟用自動清理，只顯示翻譯完成訊息
            elif not self.auto_clean_workspace_var.get():
                self.status_label.config(text=self.get_text("all_complete"))
                self.progress_bar['value'] = 0
                messagebox.showinfo(
                    self.get_text("confirm"),
                    self.get_text("all_complete")
                )

    def show_context_menu(self, event):
        """顯示右鍵選單"""
        try:
            # 獲取點擊位置對應的項目
            index = self.file_list.nearest(event.y)
            if index >= 0:
                self.file_list.selection_clear(0, tk.END)
                self.file_list.selection_set(index)
                self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def remove_selected(self):
        """移除選中的項目"""
        try:
            selected = self.file_list.curselection()
            if selected:
                self.file_list.delete(selected)
        except Exception as e:
            messagebox.showerror("錯誤", f"除檔案時發生錯誤：{str(e)}")

    def drag_item(self, event):
        """處理項目拖曳"""
        if self.drag_data["index"] is None:
            # 開始拖曳
            index = self.file_list.nearest(event.y)
            if index >= 0:
                self.drag_data["index"] = index
                self.drag_data["y"] = event.y
        else:
            # 繼續拖曳
            new_index = self.file_list.nearest(event.y)
            if new_index >= 0 and new_index != self.drag_data["index"]:
                # 獲取要移動的項目內容
                item = self.file_list.get(self.drag_data["index"])
                # 刪除原位置
                self.file_list.delete(self.drag_data["index"])
                # 插入新位置
                self.file_list.insert(new_index, item)
                # 更新拖曳數
                self.drag_data["index"] = new_index
                self.drag_data["y"] = event.y

    def drop_item(self, event):
        """處理項目放開"""
        self.drag_data = {"index": None, "y": 0}

    def create_clean_menu(self):
        """創建清理選單"""
        self.menubar = Menu(self)
        self.config(menu=self.menubar)
        
        # 創建檔案選單
        file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="檔案", menu=file_menu)
        
        # 添加清理選項
        file_menu.add_command(label="清理 SRT 檔案", command=self.clean_srt_files)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.quit)


    def toggle_clean_mode(self):
        """切換清理模式"""
        if self.clean_mode_var.get():
            self.status_label.config(text="已啟用翻譯前自動清理功能")
        else:
            self.status_label.config(text="已關閉翻譯前自動清理功能")

    def clean_srt_files(self):
        """清理選中的 SRT 檔案"""
        if not hasattr(self, "file_list"):
            messagebox.showwarning("提示", "此功能已移至新工作流程，請改用批次處理。")
            return
        if self.file_list.size() == 0:
            messagebox.showwarning("提示", "請先選擇要清理的 SRT 檔案")
            return
            
        # 創建備份目錄
        backup_path = os.path.join(os.path.dirname(self.file_list.get(0)), 'backup')
        ensure_backup_dir(backup_path)

        # 更新狀態標籤
        self.status_label.config(text="正在清理檔案...")
        self.update_idletasks()

        total_cleaned = 0
        total_files = self.file_list.size()

        for i in range(total_files):
            input_file = self.file_list.get(i)
            try:
                # 清理檔案並獲取結果
                result = clean_srt_file(input_file, create_backup=True)
                total_cleaned += result["cleaned"]
                    
                # 更新進度
                progress = (i + 1) / self.file_list.size() * 100
                self.progress_bar['value'] = progress
                self.status_label.config(text=f"正在清理檔案 {i+1}/{self.file_list.size()} ({progress:.1f}%)")
                self.update_idletasks()
                
            except Exception as e:
                messagebox.showerror("錯誤", f"處理檔案時發生錯誤: {str(e)}")
                return

        # 完成後重置進度條和狀態
        self.progress_bar['value'] = 0
        self.status_label.config(text="清理完成！")
        messagebox.showinfo("完成", "所有選中的 SRT 檔案已清理完成！\n原始檔案已備份至 backup 資料夾。")

    def show_countdown_dialog(self, message, countdown=5):
        """顯示帶有倒計時的對話框"""
        logger.debug("Showing conflict dialog countdown=%s message=%s", countdown, message)
        # 創建新視窗
        countdown_window = tk.Toplevel(self)
        countdown_window.title(self.get_text("file_conflict_title"))
        countdown_window.geometry("400x200")
        countdown_window.transient(self)  # 設置為主視窗的子視窗
        countdown_window.grab_set()  # 模態視窗
        countdown_window.resizable(False, False)  # 禁止調整視窗大小
        
        # 保存視窗引用
        self.countdown_window = countdown_window
        self.dialog_result = None

        # 創建主框架
        main_frame = ttk.Frame(countdown_window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 添加訊息標籤
        message_label = ttk.Label(main_frame, text=message, wraplength=350, justify="center")
        message_label.pack(pady=(0, 10))
        
        # 添加倒計時標籤
        self.countdown_label = ttk.Label(main_frame, text=self.get_text("auto_rename_countdown").format(countdown), font=("Arial", 10, "bold"))
        self.countdown_label.pack(pady=(0, 20))
        
        # 添加按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=(0, 10))
        
        # 設置按鈕樣式
        style = ttk.Style()
        style.configure("Action.TButton", padding=5)
        
        # 添加按鈕
        overwrite_btn = ttk.Button(
            button_frame, 
            text=self.get_text("overwrite"), 
            style="Action.TButton",
            command=lambda: self.set_dialog_result("overwrite")
        )
        overwrite_btn.pack(side=tk.LEFT, padx=5)
        
        rename_btn = ttk.Button(
            button_frame, 
            text=self.get_text("rename"), 
            style="Action.TButton",
            command=lambda: self.set_dialog_result("rename")
        )
        rename_btn.pack(side=tk.LEFT, padx=5)
        
        skip_btn = ttk.Button(
            button_frame, 
            text=self.get_text("skip"), 
            style="Action.TButton",
            command=lambda: self.set_dialog_result("skip")
        )
        skip_btn.pack(side=tk.LEFT, padx=5)
        
        # 開始倒計時
        def update_countdown():
            nonlocal countdown
            if countdown > 0 and self.dialog_result is None:
                countdown -= 1
                self.countdown_label.config(text=self.get_text("auto_rename_countdown").format(countdown))
                countdown_window.after(1000, update_countdown)
            elif self.dialog_result is None:
                self.set_dialog_result("rename")
        
        # 置中顯示視窗
        countdown_window.update_idletasks()
        width = countdown_window.winfo_width()
        height = countdown_window.winfo_height()
        x = (countdown_window.winfo_screenwidth() // 2) - (width // 2)
        y = (countdown_window.winfo_screenheight() // 2) - (height // 2)
        countdown_window.geometry(f"{width}x{height}+{x}+{y}")
        
        countdown_window.after(1000, update_countdown)
        countdown_window.wait_window()
        logger.debug("Conflict dialog closed result=%s", self.dialog_result)
        return self.dialog_result

    def set_dialog_result(self, result):
        """設置對話框結果並關閉視窗"""
        self.dialog_result = result
        logger.debug("Conflict dialog result set result=%s", result)
        if self.countdown_window:
            self.countdown_window.destroy()
            self.countdown_window = None

    def delete_selected_file(self, event=None):
        """刪除選中的檔案"""
        try:
            selected = self.file_list.curselection()
            if selected:
                self.file_list.delete(selected)
                self.status_label.config(text=self.get_text("file_removed"))
                logger.debug("Deleted selected file index=%s", selected)
        except Exception as e:
            logger.exception("Failed deleting selected file")
            messagebox.showerror(
                self.get_text("error"),
                self.get_text("error_message").format(str(e))
            )

    def _bind_config_traces(self):
        if self._config_traces_bound:
            return
        self._config_traces_bound = True
        vars_to_watch = []
        for name in (
            "clean_mode_var",
            "debug_mode_var",
            "auto_clean_workspace_var",
            "replace_original_var",
            "use_alt_prompt_var",
            "output_to_source_var",
            "enable_translation_var",
            "use_gpu_var",
        ):
            if hasattr(self, name):
                vars_to_watch.append(getattr(self, name))
        for var in vars_to_watch:
            try:
                var.trace_add("write", lambda *_: self._save_config())
            except Exception:
                pass

    def _collect_config(self) -> dict[str, Any]:
        return {
            "ui_language": self.current_language.get(),
            "translation_engine_key": self.translation_engine_key,
            "source_lang": self.source_lang.get() if hasattr(self, "source_lang") else "",
            "target_lang": self.target_lang.get() if hasattr(self, "target_lang") else "",
            "model_name": self.model_combo.get() if hasattr(self, "model_combo") else "",
            "parallel_requests": self.parallel_requests.get() if hasattr(self, "parallel_requests") else "",
            "enable_translation": bool(self.enable_translation_var.get()) if hasattr(self, "enable_translation_var") else False,
            "clean_mode": bool(self.clean_mode_var.get()),
            "debug_mode": bool(self.debug_mode_var.get()),
            "auto_clean_workspace": bool(self.auto_clean_workspace_var.get()),
            "replace_original": bool(self.replace_original_var.get()),
            "use_alt_prompt": bool(self.use_alt_prompt_var.get()),
            "output_to_source": bool(self.output_to_source_var.get()),
            "asr_model_path": self.asr_model_path.get() if hasattr(self, "asr_model_path") else "",
            "use_gpu": bool(self.use_gpu_var.get()) if hasattr(self, "use_gpu_var") else False,
            "gpu_backend": self.gpu_backend.get() if hasattr(self, "gpu_backend") else "",
            "asr_language": self.asr_lang.get() if hasattr(self, "asr_lang") else "",
            "output_format": self.output_format.get() if hasattr(self, "output_format") else "",
            "asr_output_path": self.asr_output_path.get() if hasattr(self, "asr_output_path") else "",
        }

    def _apply_config(self, config: dict[str, Any]) -> None:
        ui_language = config.get("ui_language")
        if ui_language in self.translations:
            self.current_language.set(ui_language)

        self.translation_engine_key = config.get("translation_engine_key", self.translation_engine_key)
        self.translation_engine_var.set(self._label_for_engine(self.translation_engine_key))

        self.update_ui_language()

        source_lang = config.get("source_lang")
        if hasattr(self, "source_lang") and source_lang:
            if source_lang in self.source_lang["values"]:
                self.source_lang.set(source_lang)

        target_lang = config.get("target_lang")
        if hasattr(self, "target_lang") and target_lang:
            if target_lang in self.target_lang["values"]:
                self.target_lang.set(target_lang)

        model_name = config.get("model_name")
        if hasattr(self, "model_combo") and model_name:
            self.model_combo.set(model_name)

        parallel_requests = config.get("parallel_requests")
        if hasattr(self, "parallel_requests") and parallel_requests:
            self.parallel_requests.set(str(parallel_requests))

        if hasattr(self, "enable_translation_var"):
            self.enable_translation_var.set(bool(config.get("enable_translation", self.enable_translation_var.get())))
        self.clean_mode_var.set(bool(config.get("clean_mode", self.clean_mode_var.get())))
        self.debug_mode_var.set(bool(config.get("debug_mode", self.debug_mode_var.get())))
        self.auto_clean_workspace_var.set(bool(config.get("auto_clean_workspace", self.auto_clean_workspace_var.get())))
        self.replace_original_var.set(bool(config.get("replace_original", self.replace_original_var.get())))
        self.use_alt_prompt_var.set(bool(config.get("use_alt_prompt", self.use_alt_prompt_var.get())))
        self.output_to_source_var.set(bool(config.get("output_to_source", self.output_to_source_var.get())))

        if hasattr(self, "asr_model_path") and config.get("asr_model_path"):
            self.asr_model_path.delete(0, tk.END)
            self.asr_model_path.insert(0, config.get("asr_model_path"))
        if hasattr(self, "use_gpu_var"):
            self.use_gpu_var.set(bool(config.get("use_gpu", self.use_gpu_var.get())))
        if hasattr(self, "gpu_backend") and config.get("gpu_backend"):
            self.gpu_backend.set(config.get("gpu_backend"))
        if hasattr(self, "asr_lang") and config.get("asr_language"):
            if config.get("asr_language") in self.asr_lang["values"]:
                self.asr_lang.set(config.get("asr_language"))
        if hasattr(self, "output_format") and config.get("output_format"):
            if config.get("output_format") in self.output_format["values"]:
                self.output_format.set(config.get("output_format"))
        if hasattr(self, "asr_output_path") and config.get("asr_output_path"):
            self.asr_output_path.delete(0, tk.END)
            self.asr_output_path.insert(0, config.get("asr_output_path"))

        self.toggle_translation_options()
        self.toggle_translation_engine_options()

    def _load_config(self) -> None:
        try:
            if not os.path.exists(self.config_path):
                self._save_config()
                return
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._apply_config(data)
                logger.debug("Config loaded path=%s", self.config_path)
        except Exception as exc:
            logger.warning("Failed to load config path=%s error=%s", self.config_path, exc)

    def _save_config(self) -> None:
        try:
            data = self._collect_config()
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2, sort_keys=True)
            logger.debug("Config saved path=%s", self.config_path)
        except Exception as exc:
            logger.warning("Failed to save config path=%s error=%s", self.config_path, exc)

    def _on_close(self):
        self._save_config()
        self.destroy()
