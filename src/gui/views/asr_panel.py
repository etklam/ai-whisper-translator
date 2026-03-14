import tkinter as tk
from tkinter import ttk


def build_asr_panel(app, parent):
    app.asr_model_frame = ttk.LabelFrame(parent, text=app.get_text("whisper_model_section"), style="Card.TLabelframe")
    app.asr_model_frame.pack(pady=(0, 12), fill=tk.X)

    model_path_frame = ttk.Frame(app.asr_model_frame)
    model_path_frame.pack(fill=tk.X, padx=6, pady=(4, 2))

    app.asr_model_label = ttk.Label(model_path_frame, text=app.get_text("whisper_model_label"))
    app.asr_model_label.pack(side=tk.LEFT, padx=5)

    app.asr_model_path = ttk.Entry(model_path_frame)
    app.asr_model_path.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    app.asr_model_path.insert(0, "whisper.cpp/models/ggml-base.bin")
    app.asr_model_path.bind("<FocusOut>", lambda _e: app._save_config())

    app.browse_model_button = ttk.Button(
        model_path_frame,
        text=app.get_text("browse"),
        command=app.browse_model,
    )
    app.browse_model_button.pack(side=tk.LEFT, padx=5)

    gpu_frame = ttk.Frame(app.asr_model_frame)
    gpu_frame.pack(fill=tk.X, padx=6, pady=(6, 2))

    app.use_gpu_var = tk.BooleanVar(value=True)
    app.use_gpu_check = ttk.Checkbutton(
        gpu_frame,
        text=app.get_text("use_gpu"),
        variable=app.use_gpu_var,
    )
    app.use_gpu_check.pack(side=tk.LEFT, padx=5)

    app.gpu_backend_label = ttk.Label(gpu_frame, text=app.get_text("gpu_backend"))
    app.gpu_backend_label.pack(side=tk.LEFT, padx=5)

    app.gpu_backend = ttk.Combobox(
        gpu_frame,
        values=app.translations[app.current_language.get()]["gpu_backend_options"],
        state="readonly",
        width=12,
    )
    app.gpu_backend.set("auto")
    app.gpu_backend.pack(side=tk.LEFT, padx=5)
    app.gpu_backend.bind("<<ComboboxSelected>>", lambda _e: app._save_config())

    app.transcribe_frame = ttk.LabelFrame(parent, text=app.get_text("transcribe_section"), style="Card.TLabelframe")
    app.transcribe_frame.pack(fill=tk.X)

    lang_select_frame = ttk.Frame(app.transcribe_frame)
    lang_select_frame.pack(fill=tk.X, padx=6, pady=(4, 2))

    app.asr_lang_label = ttk.Label(lang_select_frame, text=app.get_text("asr_language_label"))
    app.asr_lang_label.pack(side=tk.LEFT, padx=5)

    app.asr_lang = ttk.Combobox(
        lang_select_frame,
        values=app.translations[app.current_language.get()]["asr_language_options"],
        state="readonly",
    )
    app.asr_lang.set(app.translations[app.current_language.get()]["asr_language_options"][0])
    app.asr_lang.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    app.asr_lang.bind("<<ComboboxSelected>>", lambda _e: app._save_config())

    output_format_frame = ttk.Frame(app.transcribe_frame)
    output_format_frame.pack(fill=tk.X, padx=6, pady=(6, 2))

    app.output_format_label = ttk.Label(output_format_frame, text=app.get_text("output_format"))
    app.output_format_label.pack(side=tk.LEFT, padx=5)

    app.output_format = ttk.Combobox(
        output_format_frame,
        values=app.translations[app.current_language.get()]["output_format_options"],
        state="readonly",
    )
    app.output_format.set("srt")
    app.output_format.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    app.output_format.bind("<<ComboboxSelected>>", lambda _e: app._save_config())
