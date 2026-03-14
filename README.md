# AI Whisper Translator (ASR + Translation + Summary)

Desktop GUI app for audio transcription (ASR), subtitle translation, and transcript summarization. Designed for local-first workflows with optional OpenAI-compatible endpoints.

This README is a first-use guide. For architecture/maintenance details, see the technical docs linked below.

## What It Does

### Audio Transcription (ASR)
- Transcribes audio **and video** files to subtitles (SRT/TXT/JSON/Verbose)
- Downloads audio from YouTube
- Supports multiple Whisper models (tiny/base/small/medium/large)
- GPU acceleration (Metal, CUDA, HIP, Vulkan, OpenCL, CPU)

### Translation
- Translates SRT output from ASR
- Supports two engines:
  - **Ollama / OpenAI-compatible** endpoint (local or hosted)
  - **LibreTranslate** (free engine; requires fixed source language)
- Batch-tagged requests to reduce round-trips

### Summary
- Summarizes ASR output into a `.summary.txt`
- Uses the same AI engine/model settings as translation

### Config & Prompts
- GUI settings persist in `.config` (repo root)
- Secrets are not written to `.config`; API keys stay in env vars or the current GUI session
- Translation and summary prompts are editable in the GUI
- Defaults live in `src/translation/prompts.json` with per-language variants

## Prerequisites

- Python 3.10+

For translation/summary (optional):
- **OpenAI-compatible endpoint** (default: Ollama at `http://localhost:11434/v1/chat/completions`)
  - Env: `OPENAI_COMPAT_ENDPOINT`, `OPENAI_API_KEY`
  - Remote endpoints require explicit opt-in: `ALLOW_REMOTE_AI_ENDPOINTS=1`
- **LibreTranslate** (optional): `LIBRETRANSLATE_ENDPOINT`, `LIBRETRANSLATE_API_KEY`

For ASR:
- `whisper.cpp/` is included in this repo
- Whisper models live in `whisper.cpp/models/`

Optional:
- `tkinterdnd2` for drag-and-drop (already in `requirements.txt`)

## Install (Recommended: uv)

```bash
uv sync
```

Fallback (pip + requirements.txt):

```bash
pip install -r requirements.txt
```

## Start the App

Recommended:

```bash
uv run ai-whisper-translator
```

Fallback:

```bash
python main.py
```

## First Run: Configure AI Engine

1. Click **Show AI Engine Settings** (left panel switches to AI settings).
2. Set **OpenAI Endpoint** and (optional) **API Key**.
3. Choose a **Model** from the dropdown.
4. (Optional) Edit **Translation Prompt** / **Summary Prompt**.

Notes:
- Default endpoint is Ollama: `http://localhost:11434/v1/chat/completions`
- Remote endpoints are rejected unless `ALLOW_REMOTE_AI_ENDPOINTS=1` is set
- Model list is fetched from `/v1/models` of your endpoint.

## ASR + Translation + Summary (Queue Workflow)

1. Add audio/video files or YouTube URLs to the queue.
2. Configure ASR settings (model path, GPU backend, language, output format).
3. Enable **Translation** and/or **Summary**.
4. Click **Start Processing**.

Outputs:
- Transcription: `transcriptions/*.srt` (or chosen format)
- Summary: `*.summary.txt` next to the output
- Translation: suffix-based SRT (e.g., `movie.zh_tw.srt`)

## Translation Engine Notes

### Ollama / OpenAI-Compatible
- Uses `OPENAI_COMPAT_ENDPOINT` + `OPENAI_API_KEY`
- Default is Ollama local server
- Local endpoints are trusted by default; remote endpoints are opt-in

### LibreTranslate (Free)
- Requires fixed source language (no auto-detect)
- Configure via UI or env vars

## Output and Backup Rules

### Translation
- Default output adds language suffix (e.g., `movie.zh_tw.srt`)
- If target exists: coordinator auto-resolves with rename by default
- If **Replace Original** is enabled, original is backed up to `backup/`

## Dependency Updates

- App startup does not install or update packages
- Update `yt-dlp` manually when needed:

```bash
uv pip install --upgrade yt-dlp
```

### ASR
- Output file saved to configured directory
- SRT includes timestamps
- TXT has plain text
- JSON includes timing + metadata
- Verbose includes segment time ranges

## Quick Troubleshooting

### Model list is empty
- Ensure your endpoint is reachable
- For Ollama: `ollama serve` and `ollama list`

### Translation fails immediately
- Confirm endpoint and API key
- Try a smaller model or lower parallel requests

### Whisper model not found
- Verify model path points to a valid `.bin`
- Models are in `whisper.cpp/models/`

### GPU acceleration not working
- Ensure backend is supported by your hardware
- Try `auto` or `cpu`

## Documentation

- Technical docs (EN): `docs/TECHNICAL.md`
- Technical docs (ZH-TW): `docs/TECHNICAL_ZH.md`
- Packaging notes: `docs/packaging.md`

## License

MIT License. See `LICENSE`.
