# Technical Documentation (English)

This document is for maintainers and contributors.

## 1. Scope and Current State

- Runtime is Python.
- Entry point: `main.py` → `src/main.py`.
- GUI: `src/gui/app.py` (single-page workflow with queue + AI engine panel).
- Domain/application/infrastructure layering exists and is actively used.
- TypeScript under `src/*.ts` is scaffolding and not in the runtime path.
- Package management: uv-first with pip fallback.

## 1.1 Development Status (2026-03-15)

Implemented and working:
- ASR transcription via provider split:
  - Windows target provider: `Const-me/Whisper`
  - macOS provider: `whisper.cpp` with Metal support
- Translation via OpenAI-compatible endpoints (default Ollama) and LibreTranslate
- Summary generation from ASR output
- Batch-tagged translation requests
- Queue-based ASR processing with optional translate/summary
- GPU backends with CPU fallback
- Multi-format outputs (SRT/TXT/JSON/Verbose)
- Config persistence in `.config`
- Typed settings store and extracted GUI presenters
- Local-first endpoint policy and filesystem validation
- Structured workflow results for translation and queue execution
- Typed queue inputs and truthful queue item states in the UI

In progress / next focus:
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
- GUI presenters build typed workflow requests and run coordinators asynchronously.
- Translation, ASR, queue, completion, and clean workflows are split into focused helpers.
- Queue execution reports structured `QueueItemResult` objects instead of relying on status-string parsing.

## 3. Module Responsibilities

### Application
- `src/application/`
  - `models.py`: request/result models (`TranslationRequest`, `ExecutionSummary`, `QueueItemResult`, `SourceQueueItem`)
  - `events.py`: progress events (`ProgressEvent`)
  - `endpoint_policy.py`: normalize + validate OpenAI-compatible endpoints
  - `path_validation.py`: file/path guard layer
  - `translation_coordinator.py`: translation orchestration + retries + batch tagging
  - `asr_coordinator.py`: ASR orchestration through provider factory

### Domain
- `src/domain/`
  - service protocols + domain errors

### Infrastructure
- `src/infrastructure/`
  - `asr/providers.py`: provider resolution and factory
  - `asr/const_me_provider.py`: Windows `Const-me/Whisper` adapter scaffold
  - `asr/whisper_cpp_provider.py`: macOS `whisper.cpp` adapter
  - `translation/ollama_translation_client.py`: OpenAI-compatible HTTP client
  - `translation/libretranslate_client.py`: LibreTranslate client
  - `prompt/json_prompt_provider.py`: prompt loading from JSON
  - `subtitles/pysrt_subtitle_repository.py`: subtitle adapters

### ASR
- `src/asr/`
  - `whisper_wrapper.py`: `whisper.cpp` ctypes bindings
  - `whisper_transcriber.py`: `whisper.cpp` orchestration
  - `audio_downloader.py`: yt-dlp download
  - `audio_converter.py`: ffmpeg/soundfile conversion

### GUI
- `src/gui/app.py`: Tkinter single-page UI
  - Left: queue (or AI Engine panel)
  - Right: ASR + Translation + Output settings
- `src/gui/presenters/`: queue workflow, queue execution, translation runner, completion handling, clean workflow, UI language
- `src/gui/views/`: focused widget-construction modules
- `src/gui/config/settings_store.py`: typed settings IO boundary
- `src/gui/resources/i18n.py`: translation loading

### Utilities
- `src/utils/srt_io.py`: SRT read/write boundary using standard file IO around `pysrt`

## 4. End-to-End Flows

### Queue (ASR → Optional Translation → Optional Summary)

1. User adds audio/video files or YouTube URLs.
2. GUI resolves output path + runs ASR request.
3. If enabled, translation runs on the output SRT and returns structured per-file results.
4. If enabled, summary is generated into `*.summary.txt`.
5. Queue item is marked complete only after all enabled stages finish.
6. Queue list shows pending / processing / done / failed per item.

### Translation (Coordinator Path)

- GUI builds `TranslationRequest` with UI language.
- Coordinator performs batch-tagged requests to OpenAI-compatible endpoint.
- Retries on `ExternalServiceError`.
- Completion returns `ExecutionSummary` with per-file `file_results`, not just aggregate counts.

## 5. Configuration and Defaults

### Translation / AI Engine
- OpenAI-compatible endpoint default: `http://localhost:11434/v1/chat/completions`
- Env overrides: `OPENAI_COMPAT_ENDPOINT`, `OPENAI_API_KEY`
- Remote endpoints are blocked unless `ALLOW_REMOTE_AI_ENDPOINTS=1`
- LibreTranslate endpoint: `LIBRETRANSLATE_ENDPOINT`
- Prompt file: `src/translation/prompts.json`
- GUI prompt overrides stored in `.config`

### ASR
- Windows default provider in config: `const_me`
- macOS default provider in config: `whisper_cpp`
- Whisper library path: `whisper.cpp/build/src/libwhisper.dylib`
- Default model path: `whisper.cpp/models/ggml-base.bin`
- GPU backends: auto/metal/cuda/hip/vulkan/opencl/cpu
- Output formats: srt/txt/json/verbose

### Config Persistence
- `.config` in repo root persists GUI state
- API keys are intentionally excluded from persisted config
- Includes AI engine settings and prompt overrides per UI language

## 6. Prompt System

- `JsonPromptProvider` supports per-language keys:
  - `default_prompt_{lang}` / `alt_prompt_{lang}`
  - `summary_prompt_{lang}`
- GUI override takes precedence and is stored in `.config`
- `use_alt_prompt` toggles alternate prompt

## 7. ASR System
- Windows runtime target is `Const-me/Whisper`, which is Windows-only and DirectCompute/D3D11 based
- macOS runtime remains `whisper.cpp` with Metal
- `whisper.cpp/` stays bundled in repo for the macOS path and shared GGML model storage
- Audio conversion pipeline: ffmpeg → 16kHz mono PCM float32

## 8. Output and Conflict Handling

- Translation output naming via `src/utils/file_utils.py`
- SRT loading/saving goes through `src/utils/srt_io.py`
- Replace mode backs up original into `backup/`
- Coordinator owns output conflict resolution; default policy is rename
- Path validation runs before backup/save operations

## 9. Error Handling and Retry

- API failures are wrapped as `ExternalServiceError`
- Coordinator retries service failures (`max_retries`)
- Summary generation returns a failed queue stage and preserves earlier outputs
- Auto-clean removes only successful translation inputs on partial success

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
