import tkinter as tk
from tkinter import ttk, filedialog, messagebox, Menu
import os
import sys
import logging
import subprocess
import json
import pysrt
import threading

from src.application.endpoint_policy import build_models_endpoint, normalize_openai_endpoint
from src.application.path_validation import ensure_output_directory
from src.application.settings_models import AppSettings
from src.gui.config.settings_store import (
    default_settings_path,
    load_settings,
    save_settings,
    snapshot_settings,
    with_endpoint_default,
)
from src.gui.presenters.clean_workflow import run_clean_workflow
from src.gui.presenters.completion_handling import (
    resolve_translation_completion,
)
from src.gui.presenters.queue_controller import (
    QueueController,
    build_source_queue,
    queue_status_text,
)
from src.gui.presenters.queue_execution import (
    resolve_asr_output_path,
    run_asr_request,
    run_queue_item,
    run_summary_for_output,
    run_translation_for_output,
)
from src.gui.presenters.queue_workflow import (
    handle_queue_item_done,
    process_next_queue_item,
    queue_item_label,
    start_queue_processing,
    stop_queue_processing,
)
from src.gui.presenters.translation_runner import (
    build_translation_request,
    run_translation_request,
)
from src.gui.presenters.ui_language import apply_ui_language, next_language
from src.gui.resources.i18n import get_translation, load_translations
from src.gui.views.ai_settings_panel import build_ai_settings_panel
from src.gui.views.asr_panel import build_asr_panel
from src.gui.views.translation_panel import build_translation_panel
from src.utils.file_utils import clean_srt_file

# 暫時禁用 tkinterdnd2（macOS 兼容性問題）
# TODO: 修復 tkinterdnd2 後重新啟用
TKDND_AVAILABLE = False
print("Note: Drag-and-drop is temporarily disabled (macOS compatibility).")

from src.infrastructure.translation.libretranslate_client import LibreTranslateClient
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient
from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider

logger = logging.getLogger(__name__)

def _build_source_queue(urls, files):
    return build_source_queue(urls, files)

def _parse_urls(text):
    return [line.strip() for line in text.splitlines() if line.strip()]

def _queue_status_text(current, total, status):
    return queue_status_text(current, total, status)

ENGINE_KEYS = ["ollama", "libretranslate"]

class App(tk.Tk):
    def __init__(self, coordinator=None, asr_coordinator=None):
        super().__init__()
        self.coordinator = coordinator
        self.asr_coordinator = asr_coordinator
        logger.debug("App initialized coordinator_present=%s asr_coordinator_present=%s tkdnd_available=%s",
                    bool(coordinator), bool(asr_coordinator), TKDND_AVAILABLE)

        # 初始化語言設定
        self.current_language = tk.StringVar(value="zh_tw")  # 預設使用繁體中文
        self.translations = load_translations()

        self.title(self.get_text("window_title"))
        self.geometry("1440x900")
        self.minsize(1280, 860)

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
        self.enable_summary_var = tk.BooleanVar(value=False)
        self.ai_engine_collapsed_var = tk.BooleanVar(value=True)
        self.translation_engine_key = "ollama"
        self.translation_engine_var = tk.StringVar(value="")
        self.free_translation_client = LibreTranslateClient()
        self.ollama_translation_client = OllamaTranslationClient()
        self.base_prompt_provider = JsonPromptProvider(
            os.path.join(os.path.dirname(__file__), "..", "translation", "prompts.json")
        )
        self.selected_audio_path = ""
        self.config_path = default_settings_path()
        self._config_traces_bound = False
        self.queue_controller = QueueController()
        self.queue_display_items = []
        self.queue_run_results = []
        self._queue_run_start_index = 0

        self.create_widgets()
        self.create_clean_menu()
        self._bind_config_traces()
        self._load_config()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _palette(self) -> dict[str, str]:
        return {
            "bg": "#F8FAFC",
            "surface": "#FFFFFF",
            "surface_alt": "#E2E8F0",
            "panel": "#EFF6FF",
            "text": "#020617",
            "muted": "#475569",
            "border": "#CBD5E1",
            "accent": "#0369A1",
            "accent_active": "#075985",
            "success": "#0F766E",
        }

    def _setup_styles(self):
        colors = self._palette()
        self.configure(bg=colors["bg"])

        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure(".", background=colors["bg"], foreground=colors["text"])
        style.configure("App.TFrame", background=colors["bg"])
        style.configure("TFrame", background=colors["surface"])
        style.configure("Panel.TFrame", background=colors["surface"])
        style.configure("Header.TFrame", background=colors["surface"])
        style.configure("Status.TFrame", background=colors["surface"])
        style.configure(
            "Card.TLabelframe",
            background=colors["surface"],
            borderwidth=1,
            relief="solid",
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            padding=12,
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=colors["surface"],
            foreground=colors["text"],
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure("TLabel", background=colors["surface"], foreground=colors["text"])
        style.configure("Muted.TLabel", background=colors["surface"], foreground=colors["muted"])
        style.configure(
            "HeroTitle.TLabel",
            background=colors["surface"],
            foreground=colors["text"],
            font=("TkDefaultFont", 18, "bold"),
        )
        style.configure(
            "HeroMeta.TLabel",
            background=colors["surface"],
            foreground=colors["muted"],
            font=("TkDefaultFont", 10),
        )
        style.configure(
            "SectionHint.TLabel",
            background=colors["surface"],
            foreground=colors["accent"],
            font=("TkDefaultFont", 9, "bold"),
        )
        style.configure(
            "Status.TLabel",
            background=colors["surface"],
            foreground=colors["success"],
            font=("TkDefaultFont", 10, "bold"),
        )
        style.configure("TButton", padding=(12, 8))
        style.map("TButton", background=[("active", colors["surface_alt"])])
        style.configure(
            "Accent.TButton",
            background=colors["accent"],
            foreground="#FFFFFF",
            borderwidth=0,
            padding=(14, 9),
        )
        style.map(
            "Accent.TButton",
            background=[("active", colors["accent_active"]), ("pressed", colors["accent_active"])],
            foreground=[("disabled", "#E2E8F0")],
        )
        style.configure(
            "Subtle.TButton",
            background=colors["panel"],
            foreground=colors["accent"],
            borderwidth=0,
            padding=(12, 8),
        )
        style.map(
            "Subtle.TButton",
            background=[("active", "#DBEAFE"), ("pressed", "#DBEAFE")],
        )
        style.configure("TCheckbutton", background=colors["surface"], foreground=colors["text"])
        style.configure(
            "TEntry",
            fieldbackground=colors["surface"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            insertcolor=colors["text"],
            padding=6,
        )
        style.configure(
            "TCombobox",
            fieldbackground=colors["surface"],
            foreground=colors["text"],
            bordercolor=colors["border"],
            lightcolor=colors["border"],
            darkcolor=colors["border"],
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", colors["surface"])],
            selectbackground=[("readonly", colors["surface"])],
            selectforeground=[("readonly", colors["text"])],
        )
        style.configure(
            "Horizontal.TProgressbar",
            background=colors["accent"],
            troughcolor="#E2E8F0",
            bordercolor="#E2E8F0",
            lightcolor=colors["accent"],
            darkcolor=colors["accent"],
            thickness=10,
        )

    def _style_text_widget(self, widget: tk.Text, *, height: int | None = None):
        colors = self._palette()
        widget.configure(
            bg=self._palette()["surface"],
            fg=colors["text"],
            insertbackground=colors["text"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=colors["accent"],
            padx=10,
            pady=8,
            font=("TkDefaultFont", 10),
            selectbackground="#BAE6FD",
        )
        if height is not None:
            widget.configure(height=height)

    def _style_listbox_widget(self, widget: tk.Listbox):
        colors = self._palette()
        widget.configure(
            bg=colors["surface"],
            fg=colors["text"],
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground=colors["border"],
            highlightcolor=colors["accent"],
            selectbackground=colors["accent"],
            selectforeground="#FFFFFF",
            activestyle="none",
            font=("TkDefaultFont", 10),
        )

    def _pipeline_summary_text(self) -> str:
        return "  ->  ".join(
            [
                self.get_text("sources_section"),
                self.get_text("asr_section"),
                self.get_text("translation_section"),
                self.get_text("output_section"),
            ]
        )

    def get_text(self, key):
        """獲取當前語言的文字"""
        return get_translation(self.translations, self.current_language.get(), key)

    def _get_openai_endpoint(self) -> str:
        if hasattr(self, "openai_endpoint"):
            value = (self.openai_endpoint.get() or "").strip()
            if value:
                return normalize_openai_endpoint(value)
        return normalize_openai_endpoint(
            os.getenv("OPENAI_COMPAT_ENDPOINT") or os.getenv("OLLAMA_ENDPOINT") or None
        )

    def _get_openai_api_key(self) -> str:
        if hasattr(self, "openai_api_key"):
            value = (self.openai_api_key.get() or "").strip()
            if value:
                return value
        return os.getenv("OPENAI_API_KEY") or os.getenv("OLLAMA_API_KEY") or ""

    def _build_ollama_client(self) -> OllamaTranslationClient:
        return OllamaTranslationClient(
            endpoint=self._get_openai_endpoint(),
            api_key=self._get_openai_api_key(),
        )

    def _build_prompt_provider(self):
        app = self
        base_provider = self.base_prompt_provider

        class _AppPromptProvider:
            def get_prompt(self, use_alt_prompt: bool, language: str | None = None) -> str:
                lang = language or app.current_language.get()
                if use_alt_prompt:
                    override = app._get_alt_translation_prompt_for_language(lang)
                    if override:
                        return override
                    return base_provider.get_prompt(use_alt_prompt=True, language=lang)
                override = app._get_translation_prompt_for_language(lang)
                if override:
                    return override
                return base_provider.get_prompt(use_alt_prompt=False, language=lang)

        return _AppPromptProvider()

    def _build_translation_request(self, file_paths):
        return build_translation_request(
            file_paths=file_paths,
            source_lang=self.source_lang.get(),
            target_lang=self.target_lang.get(),
            model_name=self.model_combo.get(),
            ui_language=self.current_language.get(),
            parallel_requests=int(self.parallel_requests.get()),
            clean_before_translate=False,
            replace_original=self.replace_original_var.get(),
            use_alt_prompt=self.use_alt_prompt_var.get(),
            output_conflict_policy="rename",
        )

    def _file_list_paths(self) -> list[str]:
        return [self.file_list.get(i) for i in range(self.file_list.size())]

    def _start_translation_request(self, file_paths, done_callback=None):
        if not self.coordinator:
            raise RuntimeError("Translation coordinator is not configured")
        try:
            translation_client = (
                self.free_translation_client if self.translation_engine_key == "libretranslate" else self._build_ollama_client()
            )
        except Exception as exc:
            logger.warning("Failed to initialize translation client error=%s", exc)
            messagebox.showwarning(self.get_text("warning"), str(exc))
            return False
        prompt_provider = self._build_prompt_provider()
        request = self._build_translation_request(file_paths)
        logger.info(
            "Dispatching coordinator request files=%s source=%s target=%s model=%s parallel=%s clean=%s replace=%s alt_prompt=%s engine=%s",
            len(request.file_paths),
            request.source_lang,
            request.target_lang,
            request.model_name,
            request.parallel_requests,
            request.clean_before_translate,
            request.replace_original,
            request.use_alt_prompt,
            self.translation_engine_key,
        )
        run_translation_request(
            self.coordinator,
            request,
            done_callback=done_callback,
            translation_client=translation_client,
            prompt_provider=prompt_provider,
        )
        return True

    def _default_summary_prompt(self, language: str | None = None) -> str:
        language = language or self.current_language.get()
        prompt_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "translation", "prompts.json")
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                key = f"summary_prompt_{language}"
                return (data.get(key) or data.get("summary_prompt", "")).strip()
        except Exception as exc:
            logger.warning("Failed to load summary prompt path=%s error=%s", prompt_path, exc)
        return ""

    def _default_translation_prompt(self, language: str | None = None) -> str:
        language = language or self.current_language.get()
        prompt_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "translation", "prompts.json")
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                key = f"default_prompt_{language}"
                return (data.get(key) or data.get("default_prompt", "")).strip()
        except Exception as exc:
            logger.warning("Failed to load translation prompt path=%s error=%s", prompt_path, exc)
        return ""

    def _default_alt_translation_prompt(self, language: str | None = None) -> str:
        language = language or self.current_language.get()
        prompt_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "translation", "prompts.json")
        )
        try:
            with open(prompt_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                key = f"alt_prompt_{language}"
                return (data.get(key) or data.get("alt_prompt", "")).strip()
        except Exception as exc:
            logger.warning("Failed to load alt translation prompt path=%s error=%s", prompt_path, exc)
        return ""

    def _get_summary_prompt(self) -> str:
        language = self.current_language.get()
        return self._get_summary_prompt_for_language(language)

    def _get_summary_prompt_for_language(self, language: str) -> str:
        if not hasattr(self, "summary_prompts_by_language"):
            self.summary_prompts_by_language = {}
        cached = self.summary_prompts_by_language.get(language)
        if cached:
            return cached
        if hasattr(self, "summary_prompt_text"):
            value = self.summary_prompt_text.get("1.0", tk.END).strip()
            if value:
                return value
        return self._default_summary_prompt(language)

    def _get_translation_prompt_for_language(self, language: str) -> str:
        if not hasattr(self, "translation_prompts_by_language"):
            self.translation_prompts_by_language = {}
        cached = self.translation_prompts_by_language.get(language)
        if cached:
            return cached
        if hasattr(self, "translation_prompt_text"):
            value = self.translation_prompt_text.get("1.0", tk.END).strip()
            if value:
                return value
        return self._default_translation_prompt(language)

    def _get_alt_translation_prompt_for_language(self, language: str) -> str:
        if not hasattr(self, "alt_translation_prompts_by_language"):
            self.alt_translation_prompts_by_language = {}
        cached = self.alt_translation_prompts_by_language.get(language)
        if cached:
            return cached
        if hasattr(self, "alt_translation_prompt_text"):
            value = self.alt_translation_prompt_text.get("1.0", tk.END).strip()
            if value:
                return value
        return self._default_alt_translation_prompt(language)

    def _set_summary_prompt_for_language(self, language: str, value: str) -> None:
        if not hasattr(self, "summary_prompts_by_language"):
            self.summary_prompts_by_language = {}
        self.summary_prompts_by_language[language] = value.strip()

    def _set_translation_prompt_for_language(self, language: str, value: str) -> None:
        if not hasattr(self, "translation_prompts_by_language"):
            self.translation_prompts_by_language = {}
        self.translation_prompts_by_language[language] = value.strip()

    def _set_alt_translation_prompt_for_language(self, language: str, value: str) -> None:
        if not hasattr(self, "alt_translation_prompts_by_language"):
            self.alt_translation_prompts_by_language = {}
        self.alt_translation_prompts_by_language[language] = value.strip()

    def _refresh_summary_prompt_text(self) -> None:
        if not hasattr(self, "summary_prompt_text"):
            return
        language = self.current_language.get()
        value = self._get_summary_prompt_for_language(language)
        self.summary_prompt_text.delete("1.0", tk.END)
        self.summary_prompt_text.insert("1.0", value)

    def _refresh_translation_prompt_text(self) -> None:
        if not hasattr(self, "translation_prompt_text"):
            return
        language = self.current_language.get()
        value = self._get_translation_prompt_for_language(language)
        self.translation_prompt_text.delete("1.0", tk.END)
        self.translation_prompt_text.insert("1.0", value)

    def _refresh_alt_translation_prompt_text(self) -> None:
        if not hasattr(self, "alt_translation_prompt_text"):
            return
        language = self.current_language.get()
        value = self._get_alt_translation_prompt_for_language(language)
        self.alt_translation_prompt_text.delete("1.0", tk.END)
        self.alt_translation_prompt_text.insert("1.0", value)

    def _reset_translation_prompt(self) -> None:
        language = self.current_language.get()
        value = self._default_translation_prompt(language)
        if hasattr(self, "translation_prompt_text"):
            self.translation_prompt_text.delete("1.0", tk.END)
            self.translation_prompt_text.insert("1.0", value)
        self._set_translation_prompt_for_language(language, value)
        self._save_config()

    def _reset_alt_translation_prompt(self) -> None:
        language = self.current_language.get()
        value = self._default_alt_translation_prompt(language)
        if hasattr(self, "alt_translation_prompt_text"):
            self.alt_translation_prompt_text.delete("1.0", tk.END)
            self.alt_translation_prompt_text.insert("1.0", value)
        self._set_alt_translation_prompt_for_language(language, value)
        self._save_config()

    def _reset_summary_prompt(self) -> None:
        language = self.current_language.get()
        value = self._default_summary_prompt(language)
        if hasattr(self, "summary_prompt_text"):
            self.summary_prompt_text.delete("1.0", tk.END)
            self.summary_prompt_text.insert("1.0", value)
        self._set_summary_prompt_for_language(language, value)
        self._save_config()

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
        if hasattr(self, "summary_prompt_text"):
            self._set_summary_prompt_for_language(
                current,
                self.summary_prompt_text.get("1.0", tk.END),
            )
        if hasattr(self, "translation_prompt_text"):
            self._set_translation_prompt_for_language(
                current,
                self.translation_prompt_text.get("1.0", tk.END),
            )
        if hasattr(self, "alt_translation_prompt_text"):
            self._set_alt_translation_prompt_for_language(
                current,
                self.alt_translation_prompt_text.get("1.0", tk.END),
            )
        new_language = next_language(current)
        self.current_language.set(new_language)
        logger.debug("UI language switched from=%s to=%s", current, new_language)
        self.update_ui_language()
        self._save_config()

    def update_ui_language(self):
        """更新UI語言"""
        apply_ui_language(self)

    def on_translation_engine_changed(self, event=None):
        label = (self.translation_engine_var.get() or "").strip()
        self.translation_engine_key = self._resolve_engine_key(label)
        logger.debug("Translation engine changed label=%s key=%s", label, self.translation_engine_key)
        self.toggle_translation_engine_options()
        self._save_config()

    def toggle_translation_engine_options(self):
        is_free = self.translation_engine_key == "libretranslate"
        if hasattr(self, "model_combo"):
            if is_free and not self.enable_summary_var.get():
                self.model_combo.configure(state="disabled")
            else:
                self.model_combo.configure(state="normal")
        if self.enable_translation_var.get():
            if hasattr(self, "use_alt_prompt_check"):
                if is_free:
                    self.use_alt_prompt_check.configure(state="disabled")
                else:
                    self.use_alt_prompt_check.configure(state="normal")
            if hasattr(self, "source_lang"):
                source_values = self.translations[self.current_language.get()]["source_lang_options"]
                if is_free:
                    source_values = [v for v in source_values if not self._is_auto_lang(v)]
                self.source_lang["values"] = source_values
                if self.source_lang.get() not in source_values:
                    self.source_lang.set(source_values[0] if source_values else "")

    def _validate_translation_settings(self) -> bool:
        if self.translation_engine_key != "libretranslate":
            return True
        source = (self.source_lang.get() or "").strip()
        if not source or self._is_auto_lang(source):
            messagebox.showwarning(self.get_text("notice"), self.get_text("fixed_lang_required"))
            return False
        return True

    def create_widgets(self):
        self._setup_styles()

        shell = ttk.Frame(self, style="App.TFrame")
        shell.pack(fill=tk.BOTH, expand=True, padx=18, pady=18)

        header_frame = ttk.Frame(shell, style="Header.TFrame")
        header_frame.pack(fill=tk.X, pady=(0, 14))

        self.hero_title_label = ttk.Label(
            header_frame,
            text=self.get_text("window_title"),
            style="HeroTitle.TLabel",
        )
        self.hero_title_label.pack(anchor="w", padx=18, pady=(16, 2))

        self.hero_meta_label = ttk.Label(
            header_frame,
            text=self._pipeline_summary_text(),
            style="HeroMeta.TLabel",
        )
        self.hero_meta_label.pack(anchor="w", padx=18, pady=(0, 16))

        content_frame = ttk.Frame(shell, style="App.TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True)
        content_frame.columnconfigure(0, weight=1, uniform="columns")
        content_frame.columnconfigure(1, weight=1, uniform="columns")
        content_frame.rowconfigure(0, weight=1)
        self._create_single_page(content_frame)

        status_frame = ttk.Frame(shell, style="Status.TFrame")
        status_frame.pack(fill=tk.X, pady=(14, 0))

        self.status_heading_label = ttk.Label(
            status_frame,
            text=self.get_text("workflow_status"),
            style="SectionHint.TLabel",
        )
        self.status_heading_label.pack(anchor="w", padx=18, pady=(16, 4))

        self.progress_bar = ttk.Progressbar(status_frame, mode="determinate")
        self.progress_bar.pack(fill=tk.X, padx=18, pady=(0, 12))

        self.status_label = ttk.Label(
            status_frame,
            text="",
            style="Status.TLabel",
            wraplength=1100,
            justify="left",
        )
        self.status_label.pack(fill=tk.X, padx=18, pady=(0, 18))

    def _create_single_page(self, parent):
        left_frame = ttk.Frame(parent, style="App.TFrame")
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(1, weight=1)

        right_frame = ttk.Frame(parent, style="App.TFrame")
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        right_frame.columnconfigure(0, weight=1)

        self.sources_frame = ttk.LabelFrame(left_frame, text=self.get_text("sources_section"), style="Card.TLabelframe")
        self.sources_frame.pack(fill=tk.X, pady=(0, 14))

        url_frame = ttk.Frame(self.sources_frame)
        url_frame.pack(fill=tk.X, padx=6, pady=4)

        self.youtube_urls_label = ttk.Label(url_frame, text=self.get_text("youtube_urls"))
        self.youtube_urls_label.pack(anchor="w")

        self.url_text = tk.Text(url_frame, height=4)
        self.url_text.pack(fill=tk.X, pady=(6, 0))
        self._style_text_widget(self.url_text, height=5)

        source_buttons = ttk.Frame(self.sources_frame)
        source_buttons.pack(fill=tk.X, padx=6, pady=(10, 2))

        self.add_urls_button = ttk.Button(
            source_buttons,
            text=self.get_text("add_urls_to_queue"),
            command=self.add_urls_to_queue,
            style="Subtle.TButton",
        )
        self.add_urls_button.pack(side=tk.LEFT, padx=(0, 8))

        self.select_audio_button = ttk.Button(
            source_buttons,
            text=self.get_text("select_audio_files"),
            command=self.select_audio_files,
        )
        self.select_audio_button.pack(side=tk.LEFT)

        self.queue_frame = ttk.LabelFrame(left_frame, text=self.get_text("queue_section"), style="Card.TLabelframe")
        self.queue_frame.pack(fill=tk.BOTH, expand=True)

        queue_list_frame = ttk.Frame(self.queue_frame)
        queue_list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 0))

        self.queue_list = tk.Listbox(queue_list_frame, width=70, height=6, selectmode=tk.SINGLE)
        self.queue_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._style_listbox_widget(self.queue_list)

        queue_scrollbar = ttk.Scrollbar(queue_list_frame, orient="vertical", command=self.queue_list.yview)
        queue_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        self.queue_list.configure(yscrollcommand=queue_scrollbar.set)

        queue_buttons = ttk.Frame(self.queue_frame)
        queue_buttons.pack(fill=tk.X, padx=6, pady=(10, 2))

        self.clear_queue_button = ttk.Button(
            queue_buttons,
            text=self.get_text("clear_queue"),
            command=self.clear_queue,
            style="Subtle.TButton",
        )
        self.clear_queue_button.pack(side=tk.LEFT)

        self.ai_engine_frame = ttk.LabelFrame(left_frame, text=self.get_text("ai_engine_section"), style="Card.TLabelframe")
        self._create_ai_engine_settings(self.ai_engine_frame)

        self.asr_frame = ttk.LabelFrame(right_frame, text=self.get_text("asr_section"), style="Card.TLabelframe")
        self.asr_frame.pack(fill=tk.X, pady=(0, 14))

        self._create_asr_settings(self.asr_frame)

        self.translation_frame = ttk.LabelFrame(right_frame, text=self.get_text("translation_section"), style="Card.TLabelframe")
        self.translation_frame.pack(fill=tk.X, pady=(0, 14))

        self.enable_translation_var = tk.BooleanVar(value=False)
        translation_toggle_frame = ttk.Frame(self.translation_frame)
        translation_toggle_frame.pack(fill=tk.X, padx=6, pady=(4, 4))

        self.enable_translation_check = ttk.Checkbutton(
            translation_toggle_frame,
            text=self.get_text("enable_translation"),
            variable=self.enable_translation_var,
            command=self.toggle_translation_options,
        )
        self.enable_translation_check.pack(side=tk.LEFT, padx=(0, 16))

        self.enable_summary_check = ttk.Checkbutton(
            translation_toggle_frame,
            text=self.get_text("enable_summary"),
            variable=self.enable_summary_var,
            command=self.toggle_translation_options,
        )
        self.enable_summary_check.pack(side=tk.LEFT)

        self.translation_options_frame = ttk.Frame(self.translation_frame)
        self.translation_options_frame.pack(fill=tk.X, padx=6, pady=(8, 2))
        self._create_translation_settings(self.translation_options_frame)

        self.output_frame = ttk.LabelFrame(right_frame, text=self.get_text("output_section"), style="Card.TLabelframe")
        self.output_frame.pack(fill=tk.X, pady=(0, 14))

        self._create_output_settings(self.output_frame)

        control_frame = ttk.Frame(right_frame)
        control_frame.pack(fill=tk.X, pady=(0, 4))

        queue_actions_frame = ttk.Frame(control_frame)
        queue_actions_frame.pack(fill=tk.X)

        self.start_queue_button = ttk.Button(
            queue_actions_frame,
            text=self.get_text("start_queue"),
            command=self.start_queue,
            style="Accent.TButton",
        )
        self.start_queue_button.pack(side=tk.LEFT, padx=(0, 8))

        self.stop_queue_button = ttk.Button(
            queue_actions_frame,
            text=self.get_text("stop_queue"),
            command=self.stop_queue,
            style="Subtle.TButton",
        )
        self.stop_queue_button.pack(side=tk.LEFT)

        language_actions_frame = ttk.Frame(control_frame)
        language_actions_frame.pack(fill=tk.X, pady=(8, 0))

        self.lang_button = ttk.Button(
            language_actions_frame,
            text=self.get_text("switch_language"),
            command=self.switch_language,
            style="Subtle.TButton",
        )
        self.lang_button.pack(side=tk.RIGHT)

        self.toggle_translation_options()
        self.toggle_translation_engine_options()

    def _create_asr_settings(self, parent):
        build_asr_panel(self, parent)

    def _create_translation_settings(self, parent):
        build_translation_panel(self, parent)

    def _create_ai_engine_settings(self, parent):
        build_ai_settings_panel(self, parent)

    def _create_output_settings(self, parent):
        output_path_frame = ttk.Frame(parent)
        output_path_frame.pack(fill=tk.X, padx=5, pady=5)

        self.asr_output_path_label = ttk.Label(output_path_frame, text=self.get_text("output_folder_label"))
        self.asr_output_path_label.pack(side=tk.LEFT, padx=5)

        self.asr_output_path = ttk.Entry(output_path_frame)
        self.asr_output_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.asr_output_path.insert(0, "transcriptions")
        self.asr_output_path.bind("<FocusOut>", lambda _e: self._save_config())

        self.browse_output_button = ttk.Button(
            output_path_frame,
            text=self.get_text("browse"),
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
        translation_state = "normal" if self.enable_translation_var.get() else "disabled"
        for child in self.translation_specific_frame.winfo_children():
            self._set_widget_state(child, translation_state)

        for child in self.ai_engine_frame.winfo_children():
            self._set_widget_state(child, "normal")

        if translation_state == "normal":
            self.toggle_translation_engine_options()
        self._save_config()

    def _get_ai_engine_toggle_text(self) -> str:
        return self.get_text("ai_engine_show") if self.ai_engine_collapsed_var.get() else self.get_text("ai_engine_hide")

    def toggle_ai_engine_visibility(self):
        self.ai_engine_collapsed_var.set(not self.ai_engine_collapsed_var.get())
        self._apply_ai_engine_visibility()
        self._save_config()

    def _apply_ai_engine_visibility(self):
        if not hasattr(self, "ai_engine_frame"):
            return
        if self.ai_engine_collapsed_var.get():
            if hasattr(self, "sources_frame") and self.sources_frame.winfo_manager() == "":
                self.sources_frame.pack(fill=tk.X, pady=(0, 14))
                self.sources_frame.config(text=self.get_text("sources_section"))
            if hasattr(self, "queue_frame") and self.queue_frame.winfo_manager() == "":
                self.queue_frame.pack(fill=tk.BOTH, expand=True)
                self.queue_frame.config(text=self.get_text("queue_section"))
            if self.ai_engine_frame.winfo_manager():
                self.ai_engine_frame.pack_forget()
        else:
            if hasattr(self, "sources_frame") and self.sources_frame.winfo_manager():
                self.sources_frame.pack_forget()
            if hasattr(self, "queue_frame") and self.queue_frame.winfo_manager():
                self.queue_frame.pack_forget()
            if not self.ai_engine_frame.winfo_manager():
                self.ai_engine_frame.pack(fill=tk.BOTH, expand=True)
        if hasattr(self, "ai_engine_toggle_button"):
            self.ai_engine_toggle_button.config(text=self._get_ai_engine_toggle_text())

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
            text=self.get_text("use_alt_prompt"),
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
        self.audio_path_label = ttk.Label(self.asr_tab, text=self.get_text("selected_file_none"))
        self.audio_path_label.pack(pady=5, padx=10, anchor='w')

        # 模型設定框架
        asr_model_frame = ttk.LabelFrame(self.asr_tab, text=self.get_text("whisper_model_section"))
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
            text=self.get_text("browse"),
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
        transcribe_frame = ttk.LabelFrame(self.asr_tab, text=self.get_text("transcribe_section"))
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

        self.asr_output_path_label = ttk.Label(output_path_frame, text=self.get_text("output_file_label"))
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
                messagebox.showwarning(self.get_text("warning"), self.get_text("file_not_srt").format(file))
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
        for item in _build_source_queue(url_list, []):
            self.queue_controller.add_item(item)
            self.queue_display_items.append(item)
            self.queue_list.insert(tk.END, queue_item_label(self, item))
            logger.debug("URL added to queue: %s", item.value)
        self.url_text.delete("1.0", tk.END)
        logger.info("URLs added to queue count=%s", len(url_list))

    def select_audio_files(self):
        file_paths = filedialog.askopenfilenames(
            title=self.get_text("choose_audio"),
            filetypes=[
                (self.get_text("audio_files"), "*.wav *.mp3 *.m4a *.flac *.ogg *.wma"),
                (self.get_text("video_files"), "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.wmv *.mpeg *.mpg"),
                (self.get_text("all_files"), "*.*")
            ]
        )
        if not file_paths:
            logger.debug("Audio file selection cancelled")
            return
        for item in _build_source_queue([], file_paths):
            self.queue_controller.add_item(item)
            self.queue_display_items.append(item)
            self.queue_list.insert(tk.END, queue_item_label(self, item))
            logger.debug("Audio file added to queue: %s", item.value)
        logger.debug("Audio files selected count=%s", len(file_paths))

    def clear_queue(self):
        self.queue_list.delete(0, tk.END)
        self.queue_controller.clear()
        self.queue_display_items = []
        self.queue_run_results = []
        self._queue_run_start_index = 0
        logger.debug("Queue cleared")

    def start_queue(self):
        start_queue_processing(self)

    def stop_queue(self):
        stop_queue_processing(self)

    def browse_output_dir(self):
        directory = filedialog.askdirectory(title=self.get_text("choose_output_folder"))
        if directory:
            self.asr_output_path.delete(0, tk.END)
            self.asr_output_path.insert(0, directory)
            self._save_config()

    def open_output_dir(self):
        output_dir = (self.asr_output_path.get() or "").strip() or "transcriptions"
        output_dir = str(ensure_output_directory(os.path.abspath(output_dir)))

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
            messagebox.showerror(self.get_text("error"), self.get_text("open_folder_failed").format(output_dir))
            logger.debug("Output directory selected: %s", directory)

    def _process_next_queue_item(self):
        process_next_queue_item(self)

    def _run_queue_item(self, item, index):
        logger.debug("Queue item execution started index=%s kind=%s", index, item.kind)
        run_queue_item(self, item, index)

    def _run_asr_request(self, audio_path, output_path):
        run_asr_request(self, audio_path, output_path)

    def _resolve_asr_output_path(self, audio_path, prefer_source_dir: bool = True):
        return resolve_asr_output_path(self, audio_path, prefer_source_dir=prefer_source_dir)

    def _run_translation_for_output(self, output_path, index):
        run_translation_for_output(self, output_path, index)

    def _run_summary_for_output(self, output_path, index):
        run_summary_for_output(self, output_path, index)

    def _on_queue_item_done(self, result):
        handle_queue_item_done(self, result)

    # ========== ASR Methods ==========
    def select_audio(self):
        """選擇音訊檔案"""
        file_path = filedialog.askopenfilename(
            title=self.get_text("choose_audio"),
            filetypes=[
                (self.get_text("audio_files"), "*.wav *.mp3 *.m4a *.flac *.ogg *.wma"),
                (self.get_text("video_files"), "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.m4v *.wmv *.mpeg *.mpg"),
                (self.get_text("all_files"), "*.*")
            ]
        )
        if file_path:
            self.selected_audio_path = file_path
            self.audio_path_label.config(text=self.get_text("selected_file").format(file_path))
            logger.debug("Audio file selected: %s", file_path)

    def browse_model(self):
        """瀏覽 Whisper 模型檔案"""
        file_path = filedialog.askopenfilename(
            title=self.get_text("choose_model"),
            filetypes=[(self.get_text("model_files"), "*.bin"), (self.get_text("all_files"), "*.*")]
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
            messagebox.showwarning(self.get_text("warning"), self.get_text("youtube_url_required"))
            return

        self.status_label.config(text=self.get_text("status_downloading"))

        def _show_download_error(error_msg):
            self._show_download_error(error_msg)

        def download_thread():
            """Download audio in background thread."""
            try:
                from src.asr.audio_downloader import AudioDownloader

                downloader = AudioDownloader(output_dir="downloads")
                audio_path = downloader.download_audio_to_wav(url)

                # Update UI from main thread
                def update_success():
                    self.audio_path_label.config(text=self.get_text("selected_file").format(audio_path))
                    self.status_label.config(text=self.get_text("status_downloaded"))
                    logger.info("Audio downloaded from YouTube: %s", audio_path)

                def update_error(error_msg):
                    messagebox.showerror(self.get_text("error"), self.get_text("download_failed"))
                    self.status_label.config(text=self.get_text("status_download_failed"))
                    logger.error("YouTube download error: %s", error_msg)

                if audio_path:
                    self.after(0, update_success)
                else:
                    self.after(0, lambda: update_error(self.get_text("download_failed")))
            except Exception as e:
                error_msg = str(e)
                self.after(0, lambda: _show_download_error(error_msg))

        # Start download in background thread
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()

    def _show_download_error(self, error_msg):
        """Show download error in main thread."""
        messagebox.showerror(self.get_text("error"), self.get_text("download_failed_detail").format(error_msg))
        self.status_label.config(text=self.get_text("status_download_failed"))
        logger.error("YouTube download error: %s", error_msg)

    def start_asr(self):
        """開始 ASR 轉錄"""
        # 檢查音訊檔案
        audio_path = self.selected_audio_path
        if not audio_path:
            messagebox.showwarning(self.get_text("warning"), self.get_text("select_audio_first"))
            return

        if not os.path.exists(audio_path):
            messagebox.showerror(self.get_text("error"), self.get_text("audio_missing").format(audio_path))
            return

        # 檢查模型路徑
        model_path = self.asr_model_path.get()
        if not os.path.exists(model_path):
            messagebox.showerror(self.get_text("error"), self.get_text("model_missing").format(model_path))
            return

        # 獲取設定
        use_gpu = self.use_gpu_var.get()
        gpu_backend = self.gpu_backend.get()
        asr_provider = getattr(self, "asr_provider", "auto")
        language = self._resolve_asr_language()
        output_format = self.output_format.get()
        output_path = self._resolve_asr_output_path(audio_path, prefer_source_dir=True)

        # 建立請求
        from src.application.asr_coordinator import ASRRequest

        request = ASRRequest(
            input_path=audio_path,
            output_path=output_path,
            model_path=model_path,
            asr_provider=asr_provider,
            language=language,
            use_gpu=use_gpu,
            gpu_backend=gpu_backend,
            n_threads=4,
            output_format=output_format,
            max_retries=1
        )

        # 執行轉錄
        self.status_label.config(text=self.get_text("status_transcribing"))

        def run_asr():
            try:
                summary = self.asr_coordinator.run(request)
                if summary.successful_files > 0:
                    self.after(0, lambda: messagebox.showinfo(
                        self.get_text("success"),
                        self.get_text("asr_complete_output").format(output_path),
                    ))
                    self.after(0, lambda: self.status_label.config(text=self.get_text("status_transcribed")))
                else:
                    self.after(0, lambda: messagebox.showerror(self.get_text("error"), self.get_text("asr_failed")))
                    self.after(0, lambda: self.status_label.config(text=self.get_text("status_transcribe_failed")))
            except Exception as e:
                logger.error("ASR error: %s", e)
                self.after(0, lambda: messagebox.showerror(
                    self.get_text("error"),
                    self.get_text("asr_failed_detail").format(e),
                ))
                self.after(0, lambda: self.status_label.config(text=self.get_text("status_transcribe_failed")))

        import threading
        thread = threading.Thread(target=run_asr, daemon=True)
        thread.start()
    # ========== End ASR Methods ==========

    def select_folder(self):
        """選擇文件夾並批量添加 SRT 檔案"""
        folder_path = filedialog.askdirectory(title=self.get_text("choose_srt_folder"))
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
        message = self.get_text("added_srt").format(added_count)
        if skipped_count > 0 or backup_count > 0:
            message += "\n" + self.get_text("skipped_srt").format(skipped_count)
            if backup_count > 0:
                message += "\n" + self.get_text("skipped_backup_srt").format(backup_count)
        
        if added_count > 0:
            messagebox.showinfo(self.get_text("done"), message)
        else:
            messagebox.showwarning(self.get_text("notice"), self.get_text("no_srt_found"))
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
        url = build_models_endpoint(self._get_openai_endpoint())
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

            def _on_clean_progress(progress):
                self.progress_bar["value"] = progress.progress_percent
                self.status_label.config(
                    text=self.get_text("cleaning_progress").format(
                        progress.current_file,
                        progress.total_files,
                        progress.progress_percent,
                        progress.total_cleaned,
                        progress.total_subtitles,
                    )
                )
                self.update_idletasks()

            try:
                clean_summary = run_clean_workflow(
                    self._file_list_paths(),
                    clean_srt_file,
                    create_backup=self.replace_original_var.get(),
                    on_progress=_on_clean_progress,
                )
            except Exception as exc:
                messagebox.showerror(
                    self.get_text("error"),
                    str(exc),
                )
                return

            self.status_label.config(
                text=self.get_text("cleaning_complete").format(
                    clean_summary.total_cleaned,
                    clean_summary.total_subtitles,
                )
            )
            logger.debug(
                "Pre-translation cleaning completed total_cleaned=%s total_subtitles=%s",
                clean_summary.total_cleaned,
                clean_summary.total_subtitles,
            )
            self.update_idletasks()

        # 重置進度條
        self.progress_bar['value'] = 0
        total_files = self.file_list.size()

        file_paths = [self.file_list.get(i) for i in range(total_files)]
        if not self._start_translation_request(file_paths, done_callback=self._on_coordinator_done):
            return

        self.status_label.config(
            text=self.get_text("translating").format(total_files)
        )

    def _on_coordinator_done(self, summary):
        self.after(0, lambda: self._on_coordinator_complete(summary))

    def _on_queue_translation_complete(self, output_path, index, summary):
        actual_output_path = summary.output_paths[0] if getattr(summary, "output_paths", None) else output_path
        logger.info(
            "Queue translation completed path=%s index=%s success=%s failed=%s",
            actual_output_path,
            index,
            summary.successful_files,
            summary.failed_files,
        )
        if summary.successful_files > 0:
            self.status_label.config(
                text=_queue_status_text(index, self.queue_controller.total, self.get_text("queue_done"))
            )
        else:
            self.status_label.config(
                text=f"{_queue_status_text(index, self.queue_controller.total, self.get_text('queue_failed'))}: {actual_output_path}"
            )

    def _on_coordinator_complete(self, summary):
        logger.info(
            "Coordinator completed total=%s success=%s failed=%s auto_clean_workspace=%s",
            summary.total_files,
            summary.successful_files,
            summary.failed_files,
            self.auto_clean_workspace_var.get(),
        )
        completion_state = resolve_translation_completion(
            summary,
            auto_clean_workspace=self.auto_clean_workspace_var.get(),
            get_text=self.get_text,
            file_paths=self._file_list_paths(),
        )
        if completion_state.clear_workspace:
            self.file_list.delete(0, tk.END)
        elif completion_state.remove_indices:
            for remove_index in completion_state.remove_indices:
                if 0 <= remove_index < self.file_list.size():
                    self.file_list.delete(remove_index)
        self.status_label.config(text=completion_state.status_text)
        if completion_state.reset_progress:
            self.progress_bar["value"] = 0
        messagebox.showinfo(
            self.get_text("confirm"),
            completion_state.dialog_text,
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
            messagebox.showerror(self.get_text("error"), self.get_text("error_message").format(str(e)))

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
        self.file_menu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label=self.get_text("menu_file"), menu=self.file_menu)
        
        # 添加清理選項
        self.file_menu.add_command(label=self.get_text("menu_clean_srt"), command=self.clean_srt_files)
        self.file_menu.add_separator()
        self.file_menu.add_command(label=self.get_text("menu_exit"), command=self.quit)


    def toggle_clean_mode(self):
        """切換清理模式"""
        if self.clean_mode_var.get():
            self.status_label.config(text=self.get_text("clean_mode_enabled"))
        else:
            self.status_label.config(text=self.get_text("clean_mode_disabled"))

    def clean_srt_files(self):
        """清理選中的 SRT 檔案"""
        if not hasattr(self, "file_list"):
            messagebox.showwarning(self.get_text("notice"), self.get_text("clean_move_notice"))
            return
        if self.file_list.size() == 0:
            messagebox.showwarning(self.get_text("notice"), self.get_text("select_srt_first"))
            return

        # 更新狀態標籤
        self.status_label.config(text=self.get_text("cleaning_files"))
        self.update_idletasks()

        def _on_clean_progress(progress):
            self.progress_bar["value"] = progress.progress_percent
            self.status_label.config(
                text=self.get_text("cleaning_progress_simple").format(
                    progress.current_file,
                    progress.total_files,
                    progress.progress_percent,
                )
            )
            self.update_idletasks()

        try:
            run_clean_workflow(
                self._file_list_paths(),
                clean_srt_file,
                create_backup=True,
                on_progress=_on_clean_progress,
            )
        except Exception as exc:
            messagebox.showerror(self.get_text("error"), self.get_text("clean_error").format(str(exc)))
            return

        # 完成後重置進度條和狀態
        self.progress_bar['value'] = 0
        self.status_label.config(text=self.get_text("cleaning_done"))
        messagebox.showinfo(self.get_text("done"), self.get_text("clean_done_detail"))

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
            "enable_summary_var",
            "ai_engine_collapsed_var",
            "use_gpu_var",
        ):
            if hasattr(self, name):
                vars_to_watch.append(getattr(self, name))
        for var in vars_to_watch:
            try:
                var.trace_add("write", lambda *_: self._save_config())
            except Exception:
                pass

    def _snapshot_settings(self) -> AppSettings:
        if hasattr(self, "summary_prompt_text"):
            self._set_summary_prompt_for_language(
                self.current_language.get(),
                self.summary_prompt_text.get("1.0", tk.END),
            )
        if hasattr(self, "translation_prompt_text"):
            self._set_translation_prompt_for_language(
                self.current_language.get(),
                self.translation_prompt_text.get("1.0", tk.END),
            )
        if hasattr(self, "alt_translation_prompt_text"):
            self._set_alt_translation_prompt_for_language(
                self.current_language.get(),
                self.alt_translation_prompt_text.get("1.0", tk.END),
            )
        return snapshot_settings({
            "ui_language": self.current_language.get(),
            "translation_engine_key": self.translation_engine_key,
            "source_lang": self.source_lang.get() if hasattr(self, "source_lang") else "",
            "target_lang": self.target_lang.get() if hasattr(self, "target_lang") else "",
            "model_name": self.model_combo.get() if hasattr(self, "model_combo") else "",
            "parallel_requests": self.parallel_requests.get() if hasattr(self, "parallel_requests") else "",
            "openai_endpoint": self._get_openai_endpoint(),
            "summary_prompt_zh_tw": self._get_summary_prompt_for_language("zh_tw"),
            "summary_prompt_zh_cn": self._get_summary_prompt_for_language("zh_cn"),
            "summary_prompt_en": self._get_summary_prompt_for_language("en"),
            "translation_prompt_zh_tw": self._get_translation_prompt_for_language("zh_tw"),
            "translation_prompt_zh_cn": self._get_translation_prompt_for_language("zh_cn"),
            "translation_prompt_en": self._get_translation_prompt_for_language("en"),
            "alt_translation_prompt_zh_tw": self._get_alt_translation_prompt_for_language("zh_tw"),
            "alt_translation_prompt_zh_cn": self._get_alt_translation_prompt_for_language("zh_cn"),
            "alt_translation_prompt_en": self._get_alt_translation_prompt_for_language("en"),
            "enable_translation": bool(self.enable_translation_var.get()) if hasattr(self, "enable_translation_var") else False,
            "enable_summary": bool(self.enable_summary_var.get()) if hasattr(self, "enable_summary_var") else False,
            "ai_engine_collapsed": bool(self.ai_engine_collapsed_var.get()) if hasattr(self, "ai_engine_collapsed_var") else True,
            "clean_mode": bool(self.clean_mode_var.get()),
            "debug_mode": bool(self.debug_mode_var.get()),
            "auto_clean_workspace": bool(self.auto_clean_workspace_var.get()),
            "replace_original": bool(self.replace_original_var.get()),
            "use_alt_prompt": bool(self.use_alt_prompt_var.get()),
            "output_to_source": bool(self.output_to_source_var.get()),
            "asr_model_path": self.asr_model_path.get() if hasattr(self, "asr_model_path") else "",
            "asr_provider": getattr(self, "asr_provider", "auto"),
            "use_gpu": bool(self.use_gpu_var.get()) if hasattr(self, "use_gpu_var") else False,
            "gpu_backend": self.gpu_backend.get() if hasattr(self, "gpu_backend") else "",
            "asr_language": self.asr_lang.get() if hasattr(self, "asr_lang") else "",
            "output_format": self.output_format.get() if hasattr(self, "output_format") else "",
            "asr_output_path": self.asr_output_path.get() if hasattr(self, "asr_output_path") else "",
        })

    def _apply_settings(self, settings: AppSettings, legacy_api_key: str = "") -> None:
        if settings.ui_language in self.translations:
            self.current_language.set(settings.ui_language)

        self.translation_engine_key = settings.translation_engine_key or self.translation_engine_key
        self.translation_engine_var.set(self._label_for_engine(self.translation_engine_key))

        self.update_ui_language()

        source_lang = settings.source_lang
        if hasattr(self, "source_lang") and source_lang:
            if source_lang in self.source_lang["values"]:
                self.source_lang.set(source_lang)

        target_lang = settings.target_lang
        if hasattr(self, "target_lang") and target_lang:
            if target_lang in self.target_lang["values"]:
                self.target_lang.set(target_lang)

        model_name = settings.model_name
        if hasattr(self, "model_combo") and model_name:
            self.model_combo.set(model_name)

        parallel_requests = settings.parallel_requests
        if hasattr(self, "parallel_requests") and parallel_requests:
            self.parallel_requests.set(str(parallel_requests))

        if hasattr(self, "openai_endpoint"):
            endpoint_value = settings.openai_endpoint or self._get_openai_endpoint()
            self.openai_endpoint.delete(0, tk.END)
            self.openai_endpoint.insert(0, endpoint_value)
        if hasattr(self, "openai_api_key"):
            api_key_value = self._get_openai_api_key()
            if legacy_api_key:
                api_key_value = legacy_api_key
                logger.warning("Legacy plaintext API key detected in config; it will not be persisted on next save")
            self.openai_api_key.delete(0, tk.END)
            self.openai_api_key.insert(0, api_key_value)
        if not hasattr(self, "summary_prompts_by_language"):
            self.summary_prompts_by_language = {}
        for lang in ("zh_tw", "zh_cn", "en"):
            key = f"summary_prompt_{lang}"
            self.summary_prompts_by_language[lang] = str(getattr(settings, key) or "").strip()
        if hasattr(self, "summary_prompt_text"):
            self._refresh_summary_prompt_text()

        if not hasattr(self, "translation_prompts_by_language"):
            self.translation_prompts_by_language = {}
        for lang in ("zh_tw", "zh_cn", "en"):
            key = f"translation_prompt_{lang}"
            self.translation_prompts_by_language[lang] = str(getattr(settings, key) or "").strip()
        if hasattr(self, "translation_prompt_text"):
            self._refresh_translation_prompt_text()

        if not hasattr(self, "alt_translation_prompts_by_language"):
            self.alt_translation_prompts_by_language = {}
        for lang in ("zh_tw", "zh_cn", "en"):
            key = f"alt_translation_prompt_{lang}"
            self.alt_translation_prompts_by_language[lang] = str(getattr(settings, key) or "").strip()
        if hasattr(self, "alt_translation_prompt_text"):
            self._refresh_alt_translation_prompt_text()

        if hasattr(self, "enable_translation_var"):
            self.enable_translation_var.set(settings.enable_translation)
        if hasattr(self, "enable_summary_var"):
            self.enable_summary_var.set(settings.enable_summary)
        if hasattr(self, "ai_engine_collapsed_var"):
            self.ai_engine_collapsed_var.set(settings.ai_engine_collapsed)
        self.clean_mode_var.set(settings.clean_mode)
        self.debug_mode_var.set(settings.debug_mode)
        self.auto_clean_workspace_var.set(settings.auto_clean_workspace)
        self.replace_original_var.set(settings.replace_original)
        self.use_alt_prompt_var.set(settings.use_alt_prompt)
        self.output_to_source_var.set(settings.output_to_source)

        if hasattr(self, "asr_model_path") and settings.asr_model_path:
            self.asr_model_path.delete(0, tk.END)
            self.asr_model_path.insert(0, settings.asr_model_path)
        self.asr_provider = settings.asr_provider or "auto"
        if hasattr(self, "use_gpu_var"):
            self.use_gpu_var.set(settings.use_gpu)
        if hasattr(self, "gpu_backend") and settings.gpu_backend:
            self.gpu_backend.set(settings.gpu_backend)
        if hasattr(self, "asr_lang") and settings.asr_language:
            if settings.asr_language in self.asr_lang["values"]:
                self.asr_lang.set(settings.asr_language)
        if hasattr(self, "output_format") and settings.output_format:
            if settings.output_format in self.output_format["values"]:
                self.output_format.set(settings.output_format)
        if hasattr(self, "asr_output_path") and settings.asr_output_path:
            self.asr_output_path.delete(0, tk.END)
            self.asr_output_path.insert(0, settings.asr_output_path)

        self._apply_ai_engine_visibility()
        self.toggle_translation_options()
        self.toggle_translation_engine_options()

    def _load_config(self) -> None:
        try:
            if not os.path.exists(self.config_path):
                self._save_config()
                return
            settings, legacy_api_key = load_settings(self.config_path)
            settings = with_endpoint_default(settings, self._get_openai_endpoint())
            self._apply_settings(settings, legacy_api_key=legacy_api_key)
            logger.debug("Config loaded path=%s", self.config_path)
        except Exception as exc:
            logger.warning("Failed to load config path=%s error=%s", self.config_path, exc)

    def _save_config(self) -> None:
        try:
            save_settings(self.config_path, self._snapshot_settings())
            logger.debug("Config saved path=%s", self.config_path)
        except Exception as exc:
            logger.warning("Failed to save config path=%s error=%s", self.config_path, exc)

    def _on_close(self):
        self._save_config()
        self.destroy()
