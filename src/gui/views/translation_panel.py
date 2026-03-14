from tkinter import ttk


def build_translation_panel(app, parent):
    app.translation_specific_frame = ttk.Frame(parent)
    app.translation_specific_frame.pack(fill="x")

    lang_frame = ttk.Frame(app.translation_specific_frame)
    lang_frame.pack(fill="x", pady=(0, 8))
    lang_frame.columnconfigure(1, weight=1)
    lang_frame.columnconfigure(3, weight=1)

    app.source_lang_label = ttk.Label(lang_frame, text=app.get_text("source_lang_label"))
    app.source_lang_label.grid(row=0, column=0, padx=(0, 8), pady=2, sticky="w")
    app.source_lang = ttk.Combobox(
        lang_frame,
        values=app.translations[app.current_language.get()]["source_lang_options"],
        state="readonly",
    )
    app.source_lang.set(app._default_source_lang())
    app.source_lang.grid(row=0, column=1, padx=(0, 14), pady=2, sticky="ew")
    app.source_lang.bind("<<ComboboxSelected>>", lambda _e: app._save_config())

    app.target_lang_label = ttk.Label(lang_frame, text=app.get_text("target_lang_label"))
    app.target_lang_label.grid(row=0, column=2, padx=(0, 8), pady=2, sticky="w")
    app.target_lang = ttk.Combobox(
        lang_frame,
        values=app.translations[app.current_language.get()]["target_lang_options"],
        state="readonly",
    )
    app.target_lang.set(app.translations[app.current_language.get()]["target_lang_options"][0])
    app.target_lang.grid(row=0, column=3, pady=2, sticky="ew")
    app.target_lang.bind("<<ComboboxSelected>>", lambda _e: app._save_config())

    engine_frame = ttk.Frame(app.translation_specific_frame)
    engine_frame.pack(fill="x", pady=(0, 8))
    engine_frame.columnconfigure(1, weight=1)

    app.translation_engine_label = ttk.Label(engine_frame, text=app.get_text("translation_engine_label"))
    app.translation_engine_label.grid(row=0, column=0, padx=(0, 8), sticky="w")
    app.translation_engine = ttk.Combobox(
        engine_frame,
        textvariable=app.translation_engine_var,
        values=app._get_engine_labels(),
        state="readonly",
    )
    app.translation_engine_var.set(app._label_for_engine(app.translation_engine_key))
    app.translation_engine.grid(row=0, column=1, sticky="ew")
    app.translation_engine.bind("<<ComboboxSelected>>", app.on_translation_engine_changed)

    checkbox_frame = ttk.Frame(app.translation_specific_frame)
    checkbox_frame.pack(fill="x")

    app.replace_original_check = ttk.Checkbutton(
        checkbox_frame,
        text=app.get_text("replace_original"),
        variable=app.replace_original_var,
    )
    app.replace_original_check.pack(side="left", padx=5)

    app.use_alt_prompt_check = ttk.Checkbutton(
        checkbox_frame,
        text=app.get_text("use_alt_prompt"),
        variable=app.use_alt_prompt_var,
    )
    app.use_alt_prompt_check.pack(side="left", padx=5)

    app.ai_engine_toggle_frame = ttk.Frame(parent)
    app.ai_engine_toggle_frame.pack(pady=5, fill="x")
    app.ai_engine_toggle_button = ttk.Button(
        app.ai_engine_toggle_frame,
        text=app._get_ai_engine_toggle_text(),
        command=app.toggle_ai_engine_visibility,
    )
    app.ai_engine_toggle_button.pack(anchor="w", padx=5)
    app._apply_ai_engine_visibility()
