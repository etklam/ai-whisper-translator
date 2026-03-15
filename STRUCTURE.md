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
│   ├── app.py               # Main UI shell and widget event handlers
│   ├── config/              # Settings persistence
│   ├── presenters/          # Queue workflow/execution, language, completion, cleaning, translation runners
│   ├── resources/           # I18n resources and loaders
│   └── views/               # Focused panel builders
├── application/             # Orchestration layer
│   ├── models.py            # Typed workflow request/result dataclasses
│   ├── events.py            # Progress events
│   ├── endpoint_policy.py   # Local-first endpoint trust policy
│   ├── path_validation.py   # Filesystem guard layer
│   ├── translation_coordinator.py
│   └── asr_coordinator.py
├── domain/                  # Protocols + domain errors
├── infrastructure/          # Concrete adapters
│   ├── translation/         # Ollama/OpenAI-compatible + LibreTranslate
│   ├── prompt/              # JSON prompt provider
│   └── subtitles/           # Pysrt repository
├── asr/                     # whisper.cpp integration + audio pipeline
├── translation/             # Prompt resources
└── utils/                   # File utils, naming, cleanup, SRT IO
```

## Key Files

- `src/gui/app.py`: GUI shell and widget wiring
- `src/gui/presenters/`: extracted GUI workflow logic and queue orchestration
- `src/translation/prompts.json`: default + per-language prompts
- `src/utils/srt_io.py`: standard-IO boundary around `pysrt`
- `.config` (repo root): GUI settings and prompt overrides, excluding API secrets

## Notes

- `src/application/translation_coordinator.py` is the single production translation path.
- Queue input/output contracts are typed (`SourceQueueItem`, `QueueItemResult`, `ExecutionSummary`).
- `src/*.ts` files are scaffolding and not part of the runtime.
