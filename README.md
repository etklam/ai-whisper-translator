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
- Windows runtime target: `Const-me/Whisper`
- macOS runtime target: `whisper.cpp` with `Metal`
- Whisper GGML models currently live under `whisper.cpp/models/`

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

## Quick Start: From Clone to First ASR Run

### 1. Clone the repo

```bash
git clone https://github.com/etklam/ai-whisper-translator.git
cd ai-whisper-translator
```

### 2. Install Python dependencies

```bash
uv sync
```

Fallback:

```bash
pip install -r requirements.txt
```

### 3. Run the setup script

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File packaging/windows/setup-whisper-cpp.ps1
```

macOS:

```bash
chmod +x packaging/macos/setup-whisper-cpp.sh
./packaging/macos/setup-whisper-cpp.sh
```

During setup:
- The script shows `Available environments`
- On Windows, use Up/Down arrows to choose the backend/environment first
- On macOS, the script builds `whisper.cpp`
- It shows `Installed models` and `Available download models`
- On Windows, use Up/Down arrows to choose the Whisper model
- Missing models are downloaded automatically
- `.config` is updated with `asr_model_path`, `asr_provider`, `gpu_backend`, and `use_gpu`

Notes:
- Empty backend input uses the platform default
- Empty model input uses `base`
- Windows currently resolves `asr_provider=const_me` in config; full automated `Const-me/Whisper` runtime installation is still being aligned with that project's Visual Studio build flow
- Windows backend labels:
  - `CPU (no GPU)`
  - `CUDA (NVIDIA)`
  - `Vulkan (AMD)`
  - `OpenVINO (Intel)`
- Windows AMD GPU users should choose `Vulkan (AMD)`
- You can skip prompts with `-Backend <name>` / `--backend <name>` and `--model <name>`

### 4. Start the app

```bash
uv run ai-whisper-translator
```

Fallback:

```bash
python main.py
```

### 5. Run your first ASR job

1. Add one audio or video file.
2. Open the ASR section.
3. Confirm the Whisper model path is filled in.
4. Set language/output if needed.
5. Start transcription.

If you only need ASR, you can stop here. Translation can be configured later.

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
- Run the platform setup script again and re-select backend/model
- Verify model path points to a valid `.bin`
- Models are in `whisper.cpp/models/`

### GPU acceleration not working
- Ensure backend is supported by your hardware
- On Windows with AMD GPU, use `Vulkan (AMD)`
- Try `cpu` if GPU init fails

## Documentation

- Technical docs (EN): `docs/TECHNICAL.md`
- Technical docs (ZH-TW): `docs/TECHNICAL_ZH.md`
- Packaging notes: `docs/packaging.md`

## License

MIT License. See `LICENSE`.
