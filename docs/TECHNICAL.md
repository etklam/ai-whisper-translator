# Technical Documentation (English)

This document is for maintainers and contributors.

## 1. Scope and Current State

- Runtime is Python.
- Entry point: `main.py` → `src/main.py`.
- GUI: `src/gui/app.py` (single-page workflow with queue + AI engine panel).
- Domain/application/infrastructure layering exists and is actively used.
- TypeScript under `src/*.ts` is scaffolding and not in the runtime path.
- Package management: uv-first with pip fallback.

## 1.1 Development Status (2026-03-14)

Implemented and working:
- ASR transcription via whisper.cpp
- Translation via OpenAI-compatible endpoints (default Ollama) and LibreTranslate
- Summary generation from ASR output
- Batch-tagged translation requests
- Queue-based ASR processing with optional translate/summary
- GPU backends with CPU fallback
- Multi-format outputs (SRT/TXT/JSON/Verbose)
- Config persistence in `.config`

In progress / next focus:
- Retire legacy translation-only UI and unify flows
- Packaging for macOS/Windows
- Expand GUI/ASR edge-case tests

## 2. Runtime Architecture

Startup path:

1. `main.py`
2. `src.main.main()`
3. `build_default_coordinator()` creates:
   - `PysrtSubtitleRepository`
   - `OllamaTranslationClient`
   - `JsonPromptProvider`
4. `App` created with coordinators
5. `event_sink` bound to GUI handlers

High-level flow:
- GUI collects input and options.
- GUI builds `TranslationRequest` and runs coordinator (when using coordinator path).
- GUI also runs legacy `TranslationThread` for certain flows.

## 3. Module Responsibilities

### Application
- `src/application/`
  - `models.py`: request models (`TranslationRequest`, `ASRRequest`)
  - `events.py`: progress events (`ProgressEvent`)
  - `translation_coordinator.py`: translation orchestration + retries + batch tagging
  - `asr_coordinator.py`: ASR orchestration with whisper.cpp

### Domain
- `src/domain/`
  - service protocols + domain errors

### Infrastructure
- `src/infrastructure/`
  - `translation/ollama_translation_client.py`: OpenAI-compatible HTTP client
  - `translation/libretranslate_client.py`: LibreTranslate client
  - `prompt/json_prompt_provider.py`: prompt loading from JSON
  - `subtitles/pysrt_subtitle_repository.py`: subtitle adapters

### ASR
- `src/asr/`
  - `whisper_wrapper.py`: ctypes bindings
  - `whisper_transcriber.py`: orchestration
  - `audio_downloader.py`: yt-dlp download
  - `audio_converter.py`: ffmpeg/soundfile conversion

### GUI
- `src/gui/app.py`: Tkinter single-page UI
  - Left: queue (or AI Engine panel)
  - Right: ASR + Translation + Output settings

### Legacy
- `src/translation/translation_thread.py`: legacy thread-based translation

## 4. End-to-End Flows

### Queue (ASR → Optional Summary → Optional Translation)

1. User adds audio/video files or YouTube URLs.
2. GUI resolves output path + runs ASR request.
3. If enabled, summary is generated into `*.summary.txt`.
4. If enabled, translation is run on the output SRT.

### Translation (Coordinator Path)

- GUI builds `TranslationRequest` with UI language.
- Coordinator performs batch-tagged requests to OpenAI-compatible endpoint.
- Retries on `ExternalServiceError`.

### Legacy Thread Path

- `TranslationThread` still performs batch translation with conflict handling.

## 5. Configuration and Defaults

### Translation / AI Engine
- OpenAI-compatible endpoint default: `http://localhost:11434/v1/chat/completions`
- Env overrides: `OPENAI_COMPAT_ENDPOINT`, `OPENAI_API_KEY`
- LibreTranslate endpoint: `LIBRETRANSLATE_ENDPOINT`
- Prompt file: `src/translation/prompts.json`
- GUI prompt overrides stored in `.config`

### ASR
- Whisper library path: `whisper.cpp/build/src/libwhisper.dylib`
- Default model path: `whisper.cpp/models/ggml-base.bin`
- GPU backends: auto/metal/cuda/hip/vulkan/opencl/cpu
- Output formats: srt/txt/json/verbose

### Config Persistence
- `.config` in repo root persists GUI state
- Includes AI engine settings and prompt overrides per UI language

## 6. Prompt System

- `JsonPromptProvider` supports per-language keys:
  - `default_prompt_{lang}` / `alt_prompt_{lang}`
  - `summary_prompt_{lang}`
- GUI override takes precedence and is stored in `.config`
- `use_alt_prompt` toggles alternate prompt

## 7. ASR System (Whisper.cpp)

- `whisper.cpp/` bundled in repo
- Uses ctypes bindings and runtime manifest for GPU backend priority
- Audio conversion pipeline: ffmpeg → 16kHz mono PCM float32

## 8. Output and Conflict Handling

- Translation output naming via `src/utils/file_utils.py`
- Replace mode backs up original into `backup/`
- GUI handles overwrite/rename/skip with countdown

## 9. Error Handling and Retry

- API failures are wrapped as `ExternalServiceError`
- Coordinator retries service failures (`max_retries`)
- Summary generation logs errors and continues queue

## 10. Testing

Recommended (uv):

```bash
uv run pytest -v
```

Fallback (pip):

```bash
$env:PYTHONPATH='.'; pytest -v
```

## 11. Packaging Notes

See `docs/packaging.md` for build helpers and specs.
