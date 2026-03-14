import tkinter as tk
from tkinter import ttk


def build_ai_settings_panel(app, parent):
    engine_frame = ttk.Frame(parent)
    engine_frame.pack(fill=tk.X, padx=6, pady=(4, 8))

    app.openai_endpoint_label = ttk.Label(engine_frame, text=app.get_text("openai_endpoint_label"))
    app.openai_endpoint_label.grid(row=0, column=0, padx=(0, 8), sticky="w")
    app.openai_endpoint = ttk.Entry(engine_frame, width=36)
    app.openai_endpoint.grid(row=0, column=1, sticky="ew")
    app.openai_endpoint.insert(0, app._get_openai_endpoint())
    app.openai_endpoint.bind("<FocusOut>", lambda _e: app._save_config())
    engine_frame.columnconfigure(1, weight=1)

    app.openai_api_key_label = ttk.Label(engine_frame, text=app.get_text("openai_api_key_label"))
    app.openai_api_key_label.grid(row=1, column=0, padx=(0, 8), pady=(8, 0), sticky="w")
    app.openai_api_key = ttk.Entry(engine_frame, width=36, show="*")
    app.openai_api_key.grid(row=1, column=1, pady=(8, 0), sticky="ew")
    app.openai_api_key.insert(0, app._get_openai_api_key())
    app.openai_api_key.bind("<FocusOut>", lambda _e: app._save_config())

    model_frame = ttk.Frame(parent)
    model_frame.pack(fill=tk.X, padx=6, pady=(0, 8))
    model_frame.columnconfigure(1, weight=1)
    model_frame.columnconfigure(3, weight=1)

    app.model_label = ttk.Label(model_frame, text=app.get_text("model_label"))
    app.model_label.grid(row=0, column=0, padx=(0, 8), sticky="w")
    app.model_combo = ttk.Combobox(model_frame, values=app.get_model_list())
    app.model_combo.set("gpt-oss:20b")
    app.model_combo.grid(row=0, column=1, padx=(0, 14), sticky="ew")
    app.model_combo.bind("<<ComboboxSelected>>", lambda _e: app._save_config())

    app.parallel_label = ttk.Label(model_frame, text=app.get_text("parallel_label"))
    app.parallel_label.grid(row=0, column=2, padx=(0, 8), sticky="w")
    app.parallel_requests = ttk.Combobox(
        model_frame,
        values=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "15", "20"],
        state="readonly",
        width=8,
    )
    app.parallel_requests.set("10")
    app.parallel_requests.grid(row=0, column=3, sticky="ew")
    app.parallel_requests.bind("<<ComboboxSelected>>", lambda _e: app._save_config())

    translation_prompt_frame = ttk.Frame(parent)
    translation_prompt_frame.pack(fill=tk.BOTH, padx=6, pady=(0, 8))

    translation_header_frame = ttk.Frame(translation_prompt_frame)
    translation_header_frame.pack(fill=tk.X)
    app.translation_prompt_label = ttk.Label(
        translation_header_frame,
        text=app.get_text("translation_prompt_label"),
    )
    app.translation_prompt_label.pack(side=tk.LEFT)
    app.reset_translation_prompt_button = ttk.Button(
        translation_header_frame,
        text=app.get_text("reset_translation_prompt"),
        command=app._reset_translation_prompt,
    )
    app.reset_translation_prompt_button.pack(side=tk.RIGHT)

    app.translation_prompt_text = tk.Text(translation_prompt_frame, height=4, wrap="word")
    app.translation_prompt_text.pack(fill=tk.X, pady=(6, 0))
    app._style_text_widget(app.translation_prompt_text, height=5)
    app.translation_prompt_text.insert("1.0", app._get_translation_prompt_for_language(app.current_language.get()))
    app.translation_prompt_text.bind("<FocusOut>", lambda _e: app._save_config())

    alt_translation_prompt_frame = ttk.Frame(parent)
    alt_translation_prompt_frame.pack(fill=tk.BOTH, padx=6, pady=(0, 8))

    alt_translation_header_frame = ttk.Frame(alt_translation_prompt_frame)
    alt_translation_header_frame.pack(fill=tk.X)
    app.alt_translation_prompt_label = ttk.Label(
        alt_translation_header_frame,
        text=app.get_text("alt_translation_prompt_label"),
    )
    app.alt_translation_prompt_label.pack(side=tk.LEFT)
    app.reset_alt_translation_prompt_button = ttk.Button(
        alt_translation_header_frame,
        text=app.get_text("reset_alt_translation_prompt"),
        command=app._reset_alt_translation_prompt,
    )
    app.reset_alt_translation_prompt_button.pack(side=tk.RIGHT)

    app.alt_translation_prompt_text = tk.Text(alt_translation_prompt_frame, height=3, wrap="word")
    app.alt_translation_prompt_text.pack(fill=tk.X, pady=(6, 0))
    app._style_text_widget(app.alt_translation_prompt_text, height=4)
    app.alt_translation_prompt_text.insert(
        "1.0",
        app._get_alt_translation_prompt_for_language(app.current_language.get()),
    )
    app.alt_translation_prompt_text.bind("<FocusOut>", lambda _e: app._save_config())

    summary_prompt_frame = ttk.Frame(parent)
    summary_prompt_frame.pack(fill=tk.BOTH, padx=6, pady=(0, 2))

    summary_header_frame = ttk.Frame(summary_prompt_frame)
    summary_header_frame.pack(fill=tk.X)
    app.summary_prompt_label = ttk.Label(summary_header_frame, text=app.get_text("summary_prompt_label"))
    app.summary_prompt_label.pack(side=tk.LEFT)
    app.reset_summary_prompt_button = ttk.Button(
        summary_header_frame,
        text=app.get_text("reset_summary_prompt"),
        command=app._reset_summary_prompt,
    )
    app.reset_summary_prompt_button.pack(side=tk.RIGHT)

    app.summary_prompt_text = tk.Text(summary_prompt_frame, height=3, wrap="word")
    app.summary_prompt_text.pack(fill=tk.X, pady=(6, 0))
    app._style_text_widget(app.summary_prompt_text, height=4)
    app.summary_prompt_text.insert("1.0", app._get_summary_prompt())
    app.summary_prompt_text.bind("<FocusOut>", lambda _e: app._save_config())
