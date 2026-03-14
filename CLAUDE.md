# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Run the application:**
```bash
python main.py
```

**Install dependencies (uv-first, pip fallback):**
```bash
uv sync
pip install -r requirements.txt  # fallback
```

**Run all tests:**
```bash
pytest
```

**Run a single test file or test:**
```bash
pytest tests/unit/application/test_translation_coordinator.py
pytest tests/unit/application/test_translation_coordinator.py::test_name
```

**Enable debug logging:**
```bash
APP_DEBUG=1 python main.py
APP_ENV=development python main.py
```

**Build whisper.cpp shared library (macOS):**
```bash
./packaging/macos/build-whisper-cpp.sh --backend metal
./packaging/macos/build-whisper-cpp.sh --backend cpu
# Full onboarding (clone + build + download model):
./packaging/macos/onboarding-whisper-cpp.sh
```

## Architecture

The app is a desktop GUI (Tkinter) for two features: SRT subtitle translation via Ollama and audio transcription via whisper.cpp.

### Layer Overview

```
src/
├── main.py               # Composition root — wires coordinators → GUI, starts mainloop
├── gui/app.py            # Tkinter UI with two tabs: Translation and ASR
├── application/          # Orchestration: coordinators, request dataclasses, ProgressEvent
├── domain/               # Service Protocol interfaces + custom exceptions
├── infrastructure/       # Concrete implementations of domain services
├── asr/                  # whisper.cpp ctypes bindings + transcription + audio utilities
├── translation/          # Legacy thread (being unified) + prompts.json
└── utils/file_utils.py   # SRT cleaning, output path computation, backups
```

### Data Flow: Translation

1. `App` (GUI) builds a `TranslationRequest` dataclass and calls `TranslationCoordinator.run()`
2. `TranslationCoordinator` orchestrates: load SRT (`SubtitleRepository`) → translate each subtitle (`TranslationClient` → Ollama HTTP) → save with backup
3. Progress is emitted as `ProgressEvent` via `coordinator.event_sink → app.on_coordinator_event`

### Data Flow: ASR

1. `App` builds an `ASRRequest` and calls `ASRCoordinator.run()`
2. Input audio is downloaded via yt-dlp or converted to 16kHz mono PCM float32 (soundfile/ffmpeg)
3. `WhisperTranscriber` calls into `whisper_wrapper.py` (ctypes bindings to `libwhisper.dylib`)
4. Progress flows back via `asr_coordinator.event_sink → app.on_asr_event`

### Dependency Injection

`src/main.py` is the composition root — it constructs all concrete implementations and injects them into coordinators. `event_sink` callbacks are assigned after `App` is constructed to avoid a circular reference.

### Service Protocols

All external service interactions are behind `typing.Protocol` interfaces in `src/domain/services/`, making them replaceable with `Mock()` in tests. The four protocols: `TranslationClient`, `SubtitleRepository`, `PromptProvider`, `ASRProvider`.

### Ollama Integration

- Endpoint: `http://localhost:11434/v1/chat/completions` (hardcoded in `src/main.py`)
- `OLLAMA_NUM_PARALLEL=5` set as env var in root `main.py` before imports
- `OllamaTranslationClient` sends system + user message, temperature 0.1, 30s timeout
- Raises `ExternalServiceError` on failure; coordinator retries up to `max_retries`
- Prompts loaded from `src/translation/prompts.json` (`default_prompt` / `alt_prompt` keys)

### whisper.cpp Bindings

- `src/asr/whisper_wrapper.py` uses `ctypes` to bind the compiled shared library
- Library path resolved at runtime via `RuntimeManifest` in `src/infrastructure/runtime/`
- GPU backend priority: macOS = metal → cpu; Windows = cuda → hip → vulkan → cpu; Linux = cuda → vulkan → cpu

### File Output Conventions

- **Translation**: appends language suffix by default (e.g. `movie.zh_tw.srt`); replace-mode backs up the original to `backup/`
- **ASR**: outputs to `transcriptions/` in SRT, TXT, JSON, or Verbose format
- Conflict resolution (Overwrite / Rename / Skip) is handled in the GUI with an auto-rename countdown

### Legacy Code

`src/translation/translation_thread.py` is a legacy background worker being unified into the coordinator pattern. Prefer the coordinator pattern for new work.

## Testing Notes

- `tests/conftest.py` provides a `fake_services` fixture with `Mock()` for all domain protocols
- GUI tests requiring Tkinter are guarded with `pytest.mark.skipif` when `tk` is unavailable
- Standalone scripts are protected from pytest collection via `if __name__ == "__main__"` guards
- Sample SRT fixtures live in `tests/fixtures/`
