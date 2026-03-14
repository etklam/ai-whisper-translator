# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

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

**Run tests:**
```bash
pytest
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

The app is a Tkinter GUI for:
- ASR transcription via whisper.cpp
- Subtitle translation via OpenAI-compatible endpoints (default Ollama)
- Optional summary generation

### Layers

```
src/
├── main.py               # Composition root
├── gui/app.py            # Tkinter UI
├── application/          # Coordinators, requests, events
├── domain/               # Protocols + errors
├── infrastructure/       # Translation clients, prompt provider, repositories
├── asr/                  # whisper.cpp bindings + audio utilities
├── translation/          # Legacy TranslationThread + prompts.json
└── utils/file_utils.py   # SRT cleanup, output paths, backups
```

### Data Flow: Translation

1. GUI builds `TranslationRequest` and calls `TranslationCoordinator.run()`
2. Coordinator orchestrates subtitle parsing → translation client → save with backup
3. Progress events flow to GUI

### Data Flow: ASR

1. GUI builds `ASRRequest` and calls `ASRCoordinator.run()`
2. Audio download/convert → whisper.cpp transcription
3. Progress events flow to GUI

### Dependency Injection

`src/main.py` constructs coordinators and injects dependencies into the GUI. Event sinks are set after `App` is constructed.

## Translation Clients

- `OllamaTranslationClient` supports OpenAI-compatible endpoints
  - Env: `OPENAI_COMPAT_ENDPOINT`, `OPENAI_API_KEY`
- `LibreTranslateClient` supports free translation backend
  - Env: `LIBRETRANSLATE_ENDPOINT`, `LIBRETRANSLATE_API_KEY`

## Prompts

- Stored in `src/translation/prompts.json`
- Supports per-language keys:
  - `default_prompt_{lang}` / `alt_prompt_{lang}`
  - `summary_prompt_{lang}`
- GUI overrides stored in `.config`

## Config

- GUI writes `.config` at repo root
- Stores AI engine settings, prompts, and UI state

## Notes

- Legacy `TranslationThread` still exists for some flows
- Prefer coordinator path for new work
