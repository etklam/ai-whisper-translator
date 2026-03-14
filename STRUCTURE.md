# Project Structure

This document summarizes the current repository layout and responsibilities.

## Top-Level Layout

```
.
├── main.py                 # Root entry point
├── src/                     # Application source
├── docs/                    # Technical docs + packaging notes
├── packaging/               # Build helpers and PyInstaller specs
├── tests/                   # Unit and integration tests
├── whisper.cpp/             # Bundled whisper.cpp repo
├── requirements.txt         # pip fallback
├── pyproject.toml           # uv-first config
└── uv.lock                  # uv lockfile
```

## src/ Modules

```
src/
├── main.py                  # Composition root (build coordinators + GUI)
├── gui/                     # Tkinter UI
│   └── app.py               # Main UI (queue + AI engine panel)
├── application/             # Orchestration layer
│   ├── models.py            # Request dataclasses
│   ├── events.py            # Progress events
│   ├── translation_coordinator.py
│   └── asr_coordinator.py
├── domain/                  # Protocols + domain errors
├── infrastructure/          # Concrete adapters
│   ├── translation/         # Ollama/OpenAI-compatible + LibreTranslate
│   ├── prompt/              # JSON prompt provider
│   └── subtitles/           # Pysrt repository
├── asr/                     # whisper.cpp integration + audio pipeline
├── translation/             # Legacy translation thread + prompts.json
└── utils/                   # File utils, naming, cleanup
```

## Key Files

- `src/gui/app.py`: GUI, queue workflow, AI engine panel, config persistence
- `src/translation/prompts.json`: default + per-language prompts
- `.config` (repo root): GUI settings and prompt overrides

## Notes

- `src/translation/translation_thread.py` is legacy but still used in some paths.
- `src/application/translation_coordinator.py` is the preferred path for new work.
- `src/*.ts` files are scaffolding and not part of the runtime.
