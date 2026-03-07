# Technical Documentation (English)

This document is for maintainers and contributors.

## 1. Scope and Current State

- Active application runtime is Python.
- Main entrypoint is [`main.py`](../main.py), which calls [`src/main.py`](../src/main.py).
- GUI is implemented in [`src/gui/app.py`](../src/gui/app.py).
- Domain/application/infrastructure layering exists and is partially integrated.
- TypeScript files under `src/*.ts` are scaffolding and are not part of the current runtime path.
- Package management now supports uv-first workflow with pip compatibility:
  - `pyproject.toml` + `uv.lock` for uv sync/run
  - `requirements.txt` preserved for pip-based installs

## 2. Runtime Architecture

Current startup path:

1. `main.py`
2. `src.main.main()`
3. `build_default_coordinator()` creates:
   - `PysrtSubtitleRepository`
   - `OllamaTranslationClient`
   - `JsonPromptProvider`
4. GUI `App` is created with `coordinator`
5. `coordinator.event_sink` is bound to `app.on_coordinator_event`

High-level flow:

- GUI collects input files and options.
- GUI builds `TranslationRequest`.
- `TranslationCoordinator.run_async()` executes file-level processing and emits progress events.

## 3. Module Responsibilities

- `src/application/`
  - `models.py`: request models (`TranslationRequest`)
  - `events.py`: progress events (`ProgressEvent`)
  - `translation_coordinator.py`: orchestration, retries, and summary
- `src/domain/`
  - service interfaces and domain errors
- `src/infrastructure/`
  - `translation/ollama_translation_client.py`: HTTP call to Ollama `/v1/chat/completions`
  - `prompt/json_prompt_provider.py`: prompt loading from JSON
  - `subtitles/pysrt_subtitle_repository.py`: subtitle file adapters
- `src/gui/`
  - Tkinter UI, file handling, event binding, progress display
- `src/translation/`
  - legacy thread-based subtitle translation pipeline (`TranslationThread`)
- `src/utils/`
  - output naming, backup creation, subtitle cleanup helpers

## 4. End-to-End Flow

### GUI-Orchestrated Path (default)

1. User loads files in UI.
2. User configures source/target language, model, and parallel requests.
3. User starts translation.
4. `TranslationRequest` is built and passed to coordinator.
5. Coordinator retries on `ExternalServiceError` up to `max_retries`.
6. Coordinator emits `ProgressEvent` to GUI.
7. GUI updates progress bar and completion state.

### Legacy Thread Path

`TranslationThread` still contains batch subtitle translation logic, output conflict handling, and saving behavior. It remains in the codebase as legacy flow.

## 5. Configuration and Defaults

- Ollama endpoint (default): `http://localhost:11434/v1/chat/completions`
- Root process env sets: `OLLAMA_NUM_PARALLEL=5` in `main.py`
- Develop mode logging triggers:
  - `APP_ENV=development` (case-insensitive), or
  - `APP_DEBUG=1`
- Logging levels:
  - develop mode: `DEBUG`
  - default mode: `INFO`
- UI default parallel requests: `10`
- `TranslationRequest.max_retries`: default `1`
- Prompt file: `src/translation/prompts.json`

## 6. Prompt System

- Prompt provider: `JsonPromptProvider`
- Reads `default_prompt` and optional `alt_prompt`
- Falls back to constant prompt when file read/parse fails
- GUI exposes `use_alt_prompt` flag in request model

## 7. File Output and Conflict Handling

- Output naming handled by `get_output_path` in `src/utils/file_utils.py`
- Default behavior appends language suffix (`.zh_tw`, `.en`, etc.)
- Replace mode writes back to original file
- In legacy thread flow, existing output conflict supports overwrite/rename/skip with timed default rename
- Backup directory: `backup/` under source file directory

## 8. Error Handling and Retry

- HTTP/API failures are wrapped as `ExternalServiceError`
- Coordinator retries only `ExternalServiceError`
- Non-service exceptions are counted as immediate file failure
- Summary object reports total/success/failed file counts

## 9. Testing

Current tests are primarily unit tests for application/domain/infrastructure behavior.

Recommended (uv):

```bash
uv run pytest -v
```

Fallback (pip environment):

```bash
$env:PYTHONPATH='.'; pytest -v
```

Notable test areas:

- coordinator retry behavior
- app event binding
- runtime backend priority manifest
- infrastructure adapter sanity

## 10. Packaging Notes

Packaging placeholders currently exist:

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

Related note: [`docs/packaging.md`](./packaging.md)

## 11. Known Limitations

- `TranslationCoordinator` currently sends `file_path` text to translation client; full subtitle parse/write flow is not unified in coordinator yet.
- Legacy and refactored paths coexist, increasing maintenance complexity.
- Some UI text remains mixed-language and can be normalized.
- TypeScript scaffolding is not integrated with Python runtime.

## 12. Extension Guide

Common extension points:

- Add or replace translation backend:
  - implement a client compatible with current translation client interface
- Add prompt variants:
  - extend `prompts.json` and update prompt provider selection logic
- Add language suffix mapping:
  - update `get_language_suffix` in `src/utils/file_utils.py`
- Improve coordinator correctness:
  - migrate subtitle-level pipeline from `TranslationThread` into coordinator and repository abstractions
