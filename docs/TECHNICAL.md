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

### Application Layer
- `src/application/`
  - `models.py`: request models (`TranslationRequest`)
  - `events.py`: progress events (`ProgressEvent`)
  - `translation_coordinator.py`: translation orchestration, retries, and summary
  - `asr_coordinator.py`: ASR orchestration with whisper.cpp integration

### Domain Layer
- `src/domain/`
  - service interfaces and domain errors

### Infrastructure Layer
- `src/infrastructure/`
  - `translation/ollama_translation_client.py`: HTTP call to Ollama `/v1/chat/completions`
  - `prompt/json_prompt_provider.py`: prompt loading from JSON
  - `subtitles/pysrt_subtitle_repository.py`: subtitle file adapters

### ASR Layer (New)
- `src/asr/`
  - `whisper_wrapper.py`: Python ctypes bindings for whisper.cpp
  - `whisper_transcriber.py`: Whisper transcriber orchestration
  - `audio_downloader.py`: YouTube audio download using yt-dlp
  - `audio_converter.py`: Audio format conversion to 16kHz mono PCM float32
  - `utils/`: ASR-specific utilities (logger, constants, helpers)

### GUI Layer
- `src/gui/`
  - `app.py`: Tkinter UI with tab-based interface (Translation + ASR)
  - File handling, event binding, progress display

### Legacy Layer
- `src/translation/`
  - legacy thread-based subtitle translation pipeline (`TranslationThread`)

### Utilities
- `src/utils/`
  - output naming, backup creation, subtitle cleanup helpers

## 4. End-to-End Flow

### Translation Flow (GUI-Orchestrated)

1. User loads SRT files in UI (Translation tab).
2. User configures source/target language, model, and parallel requests.
3. User starts translation.
4. `TranslationRequest` is built and passed to coordinator.
5. Coordinator retries on `ExternalServiceError` up to `max_retries`.
6. Coordinator emits `ProgressEvent` to GUI.
7. GUI updates progress bar and completion state.

### ASR Flow (Audio Transcription)

1. User switches to ASR tab.
2. User selects audio file OR enters YouTube URL and downloads.
3. User configures Whisper model, GPU backend, language, and output format.
4. User starts transcription.
5. `ASRRequest` is built and passed to ASRCoordinator.
6. ASRCoordinator initializes WhisperWrapper and loads model.
7. Audio is converted to 16kHz mono PCM float32 format.
8. Whisper.cpp processes audio and generates transcription segments.
9. ASRCoordinator formats output (SRT/TXT/JSON/Verbose) and saves to file.
10. ASRCoordinator emits `ProgressEvent` to GUI.
11. GUI updates progress bar and completion state.

### Legacy Thread Path

`TranslationThread` still contains batch subtitle translation logic, output conflict handling, and saving behavior. It remains in the codebase as legacy flow.

## 5. Configuration and Defaults

### Translation Configuration
- Ollama endpoint (default): `http://localhost:11434/v1/chat/completions`
- Root process env sets: `OLLAMA_NUM_PARALLEL=5` in `main.py`
- UI default parallel requests: `10`
- `TranslationRequest.max_retries`: default `1`
- Prompt file: `src/translation/prompts.json`

### ASR Configuration
- Whisper library path: `whisper.cpp/build/src/libwhisper.dylib` (auto-detected)
- Whisper model path: Configurable in GUI (default: `whisper.cpp/models/for-tests-ggml-base.bin`)
- GPU backend: Configurable in GUI (options: auto, metal, cuda, hip, vulkan, opencl, cpu)
- Thread count: Default `4` (in ASRRequest)
- Output format: Configurable in GUI (options: srt, txt, json, verbose)

### Logging Configuration
- Develop mode logging triggers:
  - `APP_ENV=development` (case-insensitive), or
  - `APP_DEBUG=1`
- Logging levels:
  - develop mode: `DEBUG`
  - default mode: `INFO`

## 6. Prompt System

- Prompt provider: `JsonPromptProvider`
- Reads `default_prompt` and optional `alt_prompt`
- Falls back to constant prompt when file read/parse fails
- GUI exposes `use_alt_prompt` flag in request model

## 7. ASR System

### Whisper.cpp Integration

The project includes a complete whisper.cpp integration:

- **whisper.cpp/**: Complete whisper.cpp repository (226 MB)
  - Pre-built `libwhisper.dylib` for macOS
  - 11 test models in `whisper.cpp/models/`
  - CMake build system for custom builds
- **WhisperWrapper**: Python ctypes bindings
  - Wraps whisper.cpp C API
  - Auto-detects library path
  - Supports all whisper.cpp features (GPU acceleration, multiple backends)
- **Transcriber**: High-level transcriber orchestration
  - Model loading with GPU fallback
  - Audio preprocessing and format conversion
  - Multi-threaded transcription
  - Progress callbacks

### GPU Acceleration

Supported backends (auto-detected based on platform):

- **macOS (Apple Silicon)**: `metal` (primary), `cpu` (fallback)
- **Windows**: `cuda`, `hip`, `vulkan`, `cpu`
- **Linux**: `cuda`, `hip`, `vulkan`, `cpu`

GPU initialization fails gracefully to CPU.

### Audio Processing

- **AudioConverter**: Converts audio to Whisper-compatible format
  - Required: 16kHz sample rate, mono channel, PCM float32
  - Uses `soundfile` library for WAV conversion
  - Uses `ffmpeg` via subprocess for other formats
- **AudioDownloader**: Downloads audio from YouTube
  - Uses `yt-dlp` for video/audio extraction
  - Supports cookies from browser
  - Converts to WAV for Whisper processing

### Output Formats

- **SRT**: Subtitles with timestamps (standard format)
- **TXT**: Plain text without timestamps
- **JSON**: Structured output with timing and metadata
- **Verbose**: Human-readable format with time ranges

## 8. File Output and Conflict Handling

- Output naming handled by `get_output_path` in `src/utils/file_utils.py`
- Default behavior appends language suffix (`.zh_tw`, `.en`, etc.)
- Replace mode writes back to original file
- In legacy thread flow, existing output conflict supports overwrite/rename/skip with timed default rename
- Backup directory: `backup/` under source file directory

## 9. Error Handling and Retry

### Translation

- HTTP/API failures are wrapped as `ExternalServiceError`
- Coordinator retries only `ExternalServiceError`
- Non-service exceptions are counted as immediate file failure
- Summary object reports total/success/failed file counts

### ASR

- Model loading failures trigger GPU-to-CPU fallback
- Audio conversion errors are wrapped and reported
- Transcription errors are wrapped in `ExternalServiceError`
- ASRCoordinator retries on transcription failures (default: 1 retry)
- GPU backend failures automatically fallback to CPU

## 10. File Output and Conflict Handling

## 11. Testing

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
- ASR WhisperWrapper initialization
- ASR coordinator workflow

### Manual Validation (Single-Page Workflow)

1. Batch YouTube URLs queue -> sequential download + transcribe.
2. Batch local audio files -> sequential transcribe.
3. Enable translation -> ASR output SRT translated.
4. One item failure does not stop the queue.
5. Stop halts queue processing after current item.

### ASR Testing Scripts

- `test_imports.py`: ASR module import tests
- `test_gui.py`: GUI integration tests
- `test_whisper_cpp.py`: whisper.cpp integration tests

## 12. Packaging Notes

Packaging placeholders currently exist:

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

Related note: [`docs/packaging.md`](./packaging.md)

## 13. Known Limitations

- `TranslationCoordinator` currently sends `file_path` text to translation client; full subtitle parse/write flow is not unified in coordinator yet.
- Legacy and refactored paths coexist, increasing maintenance complexity.
- Some UI text remains mixed-language and can be normalized.
- TypeScript scaffolding is not integrated with Python runtime.

## 14. Extension Guide

Common extension points:

- Add or replace translation backend:
  - implement a client compatible with current translation client interface
- Add prompt variants:
  - extend `prompts.json` and update prompt provider selection logic
- Add language suffix mapping:
  - update `get_language_suffix` in `src/utils/file_utils.py`
- Improve coordinator correctness:
  - migrate subtitle-level pipeline from `TranslationThread` into coordinator and repository abstractions

### ASR Extensions

- Add new Whisper models:
  - Place .bin files in `whisper.cpp/models/`
  - Update GUI model selection list
- Add custom GPU backends:
  - Modify `gpu_backend_options` in translation dictionaries
  - Update WhisperWrapper to support new backend
- Integrate transcribe→translate workflow:
  - Add workflow button in ASR tab to automatically load output into translation tab
  - Coordinate ASR and Translation coordinators
- Improve audio format support:
  - Extend AudioConverter to support additional formats
  - Add format-specific preprocessing
