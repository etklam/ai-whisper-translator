import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import os
import sys
import logging
from queue import Queue
import threading

from src.utils.file_utils import ensure_backup_dir, clean_srt_file

# 暫時禁用 tkinterdnd2（macOS 兼容性問題）
# TODO: 修復 tkinterdnd2 後重新啟用
TKDND_AVAILABLE = False
print("提示：拖放功能已暫時停用（macOS 兼容性）")

from src.translation.translation_thread import TranslationThread

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
                "window_title": "SRT 字幕翻譯器",
                "select_files": "選擇 SRT 檔案",
                "select_folder": "文件夾批量新增",
                "source_lang_label": "原文語言:",
                "target_lang_label": "目標語言:",
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
                "source_lang_options": ["日文", "英文", "韓文", "法文", "德文", "西班牙文", "義大利文", "葡萄牙文", "俄文", "阿拉伯文", "印地文", "印尼文", "越南文", "泰文", "馬來文", "自動偵測"],
                "target_lang_options": ["繁體中文", "英文", "日文", "韓文", "法文", "德文", "西班牙文", "義大利文", "葡萄牙文", "俄文", "阿拉伯文", "印地文", "印尼文", "越南文", "泰文", "馬來文"],
                "switch_language": "Switch to English",
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
                "start_asr": "開始轉錄",
                "asr_not_available": "ASR 功能不可用",
                "asr_not_available_msg": "Whisper transcriber not available. Please install whisper.cpp library and set up the model path.",
            },
            "en": {
                "window_title": "SRT Subtitle Translator",
                "select_files": "Select SRT Files",
                "select_folder": "Add Folder",
                "source_lang_label": "Source Language:",
                "target_lang_label": "Target Language:",
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
                "source_lang_options": ["Japanese", "English", "Korean", "French", "German", "Spanish", "Italian", "Portuguese", "Russian", "Arabic", "Hindi", "Indonesian", "Vietnamese", "Thai", "Malay", "Auto Detect"],
                "target_lang_options": ["Traditional Chinese", "English", "Japanese", "Korean", "French", "German", "Spanish", "Italian", "Portuguese", "Russian", "Arabic", "Hindi", "Indonesian", "Vietnamese", "Thai", "Malay"],
                "switch_language": "切換至中文",
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
                "start_asr": "Start Transcription",
                "asr_not_available": "ASR Not Available",
                "asr_not_available_msg": "Whisper transcriber not available. Please install whisper.cpp library and set up the model path.",
            }
        }

        self.title(self.get_text("window_title"))
        self.geometry("600x600")

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
        self.queue_items = []
        self.queue_total = 0
        self.is_running = False

        self.create_widgets()
        self.create_clean_menu()

    def get_text(self, key):
        """獲取當前語言的文字"""
        return self.translations[self.current_language.get()].get(key, key)

    def switch_language(self):
        """切換語言"""
        current = self.current_language.get()
        new_language = "en" if current == "zh_tw" else "zh_tw"
        self.current_language.set(new_language)
        logger.debug("UI language switched from=%s to=%s", current, new_language)
        self.update_ui_language()

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

        if hasattr(self, "asr_lang"):
            self.asr_lang['values'] = self.translations[self.current_language.get()]["asr_language_options"]
        if hasattr(self, "target_lang"):
            self.target_lang['values'] = self.translations[self.current_language.get()]["target_lang_options"]

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
        self.status_label = ttk.Label(status_frame, text="", wraplength=550, justify="center")
        self.status_label.pack(fill=tk.BOTH, expand=True)

    def _create_single_page(self, parent):
        sources_frame = ttk.LabelFrame(parent, text=self.get_text("sources_section"))
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

        queue_frame = ttk.LabelFrame(parent, text=self.get_text("queue_section"))
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

        asr_frame = ttk.LabelFrame(parent, text=self.get_text("asr_section"))
        asr_frame.pack(fill=tk.X, padx=10, pady=5)

        self._create_asr_settings(asr_frame)

        translation_frame = ttk.LabelFrame(parent, text=self.get_text("translation_section"))
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

        output_frame = ttk.LabelFrame(parent, text=self.get_text("output_section"))
        output_frame.pack(fill=tk.X, padx=10, pady=5)

        self._create_output_settings(output_frame)

        control_frame = ttk.Frame(parent)
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

    def _create_asr_settings(self, parent):
        asr_model_frame = ttk.LabelFrame(parent, text="Whisper 模型設定")
        asr_model_frame.pack(pady=5, padx=10, fill=tk.X)

        model_path_frame = ttk.Frame(asr_model_frame)
        model_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_model_label = ttk.Label(model_path_frame, text=self.get_text("whisper_model_label"))
        self.asr_model_label.pack(side=tk.LEFT, padx=5)

        self.asr_model_path = ttk.Entry(model_path_frame)
        self.asr_model_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_model_path.insert(0, "whisper.cpp/models/for-tests-ggml-base.bin")

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
        self.asr_lang.set("自動偵測")
        self.asr_lang.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

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

    def _create_translation_settings(self, parent):
        lang_frame = ttk.Frame(parent)
        lang_frame.pack(pady=5, fill=tk.X)

        self.target_lang_label = ttk.Label(lang_frame, text=self.get_text("target_lang_label"))
        self.target_lang_label.grid(row=0, column=0, padx=5)
        self.target_lang = ttk.Combobox(
            lang_frame,
            values=self.translations[self.current_language.get()]["target_lang_options"]
        )
        self.target_lang.set(self.translations[self.current_language.get()]["target_lang_options"][0])
        self.target_lang.grid(row=0, column=1, padx=5)

        model_frame = ttk.Frame(parent)
        model_frame.pack(pady=5, fill=tk.X)

        self.model_label = ttk.Label(model_frame, text=self.get_text("model_label"))
        self.model_label.grid(row=0, column=0, padx=5)
        self.model_combo = ttk.Combobox(model_frame, values=self.get_model_list())
        self.model_combo.set("gpt-oss:20b")
        self.model_combo.grid(row=0, column=1, padx=5)

        self.parallel_label = ttk.Label(model_frame, text=self.get_text("parallel_label"))
        self.parallel_label.grid(row=0, column=2, padx=5)
        self.parallel_requests = ttk.Combobox(
            model_frame,
            values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20"]
        )
        self.parallel_requests.set("10")
        self.parallel_requests.grid(row=0, column=3, padx=5)

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

        self.browse_output_button = ttk.Button(
            output_path_frame,
            text="瀏覽",
            command=self.browse_output_dir
        )
        self.browse_output_button.pack(side=tk.LEFT, padx=5)

    def toggle_translation_options(self):
        state = "normal" if self.enable_translation_var.get() else "disabled"
        for child in self.translation_options_frame.winfo_children():
            self._set_widget_state(child, state)

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
        self.asr_model_path.insert(0, "whisper.cpp/models/for-tests-ggml-base.bin")

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
        self.asr_lang.set("自動偵測")
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
        for line in _parse_urls(urls):
            item = {"kind": "url", "value": line}
            self.queue_items.append(item)
            self.queue_list.insert(tk.END, _queue_item_label(item))
        self.url_text.delete("1.0", tk.END)

    def select_audio_files(self):
        file_paths = filedialog.askopenfilenames(
            title="選擇音訊檔案",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.m4a *.flac *.ogg *.wma"),
                ("All files", "*.*")
            ]
        )
        if not file_paths:
            return
        for path in file_paths:
            item = {"kind": "file", "value": path}
            self.queue_items.append(item)
            self.queue_list.insert(tk.END, _queue_item_label(item))
        logger.debug("Audio files selected count=%s", len(file_paths))

    def clear_queue(self):
        self.queue_list.delete(0, tk.END)
        self.queue_items = []
        self.queue_total = 0
        logger.debug("Queue cleared")

    def start_queue(self):
        logger.info("Start queue requested")
        if self.is_running:
            return
        if self.url_text.get("1.0", tk.END).strip():
            self.add_urls_to_queue()
        if not self.queue_items:
            messagebox.showwarning("提示", "請先加入待處理項目")
            return
        self.is_running = True
        self.queue_total = len(self.queue_items)
        self._process_next_queue_item()

    def stop_queue(self):
        logger.info("Stop queue requested")
        self.is_running = False

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="選擇輸出資料夾")
        if directory:
            self.asr_output_path.delete(0, tk.END)
            self.asr_output_path.insert(0, directory)
            logger.debug("Output directory selected: %s", directory)

    def _process_next_queue_item(self):
        if not self.is_running:
            return
        item = _pop_next_queue_item(self.queue_items)
        if item is None:
            self.is_running = False
            self.status_label.config(text="佇列完成")
            return
        current_index = self.queue_total - len(self.queue_items)
        self.status_label.config(text=_queue_status_text(current_index, self.queue_total, "處理中"))
        self._run_queue_item(item, current_index)

    def _run_queue_item(self, item, index):
        def _run():
            try:
                if item["kind"] == "url":
                    from src.asr.audio_downloader import AudioDownloader
                    downloader = AudioDownloader(output_dir="downloads")
                    audio_path = downloader.download_audio_to_wav(item["value"])
                else:
                    audio_path = item["value"]

                if not audio_path or not os.path.exists(audio_path):
                    raise FileNotFoundError(f"音訊檔案不存在：{audio_path}")

                output_path = self._resolve_asr_output_path(audio_path)
                self._run_asr_request(audio_path, output_path)
                if _should_translate(self.enable_translation_var.get()):
                    self._run_translation_for_output(output_path, index)
                self.after(0, lambda: self._on_queue_item_done(index, True, output_path))
            except Exception as exc:
                logger.error("Queue item failed index=%s error=%s", index, exc)
                self.after(0, lambda: self._on_queue_item_done(index, False, str(exc)))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

    def _run_asr_request(self, audio_path, output_path):
        if not self.asr_coordinator:
            raise RuntimeError(self.get_text("asr_not_available"))

        from src.application.asr_coordinator import ASRRequest

        language_map = {
            "自動偵測": None,
            "英文": "en",
            "繁體中文": "zh",
            "簡體中文": "zh",
            "日文": "ja",
            "韓文": "ko",
            "法文": "fr",
            "德文": "de",
            "西班牙文": "es",
            "Auto Detect": None,
            "English": "en",
            "Traditional Chinese": "zh",
            "Simplified Chinese": "zh",
            "Japanese": "ja",
            "Korean": "ko",
            "French": "fr",
            "German": "de",
            "Spanish": "es",
        }
        language = language_map.get(self.asr_lang.get(), None)

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

    def _resolve_asr_output_path(self, audio_path):
        output_dir = self.asr_output_path.get().strip() or "transcriptions"
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
        thread = TranslationThread(
            output_path,
            "自動偵測",
            self.target_lang.get(),
            self.model_combo.get(),
            self.parallel_requests.get(),
            self.update_progress,
            self.file_translated,
            self.debug_mode_var.get(),
            self.replace_original_var.get(),
            self.use_alt_prompt_var.get()
        )
        thread.set_app(self)
        thread.start()
        thread.join()

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
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.audio_path_label.config(text=f"選擇的檔案：{file_path}")
            self.audio_path_label.cget("from")
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
        language_map = {
            "自動偵測": None,
            "英文": "en",
            "繁體中文": "zh",
            "簡體中文": "zh",
            "日文": "ja",
            "韓文": "ko",
            "法文": "fr",
            "德文": "de",
            "西班牙文": "es",
        }
        language = language_map.get(self.asr_lang.get(), None)
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
                    
                    # 檢查是否已在列表中
                    already_exists = False
                    for i in range(self.file_list.size()):
                        if self.file_list.get(i) == full_path:
                            already_exists = True
                            skipped_count += 1
                            break
                    
                    if not already_exists:
                        self.file_list.insert(tk.END, full_path)
                        added_count += 1

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
        url = "http://localhost:11434/v1/models"
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

        if self.coordinator:
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
                self.replace_original_var.get()
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
                for i in range(self.file_list.size()):
                    if os.path.basename(self.file_list.get(i)) in message:
                        self.file_list.delete(i)
                        break
            
            # 如果檔案列表為空且啟用了自動清理，顯示完成訊息
            if self.file_list.size() == 0 and self.auto_clean_workspace_var.get():
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
