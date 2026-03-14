# AI Whisper Translator (SRT + ASR) - Quick Start

Desktop GUI tool for translating `.srt` subtitle files and transcribing audio to subtitles with local AI models.

Use this README for first-time setup and your first successful use. For architecture and maintenance details, use the technical docs linked below.

## What It Does

### Translation
- Translates one or many SRT files
- Supports drag-and-drop (when `tkinterdnd2` is installed)
- Supports folder import and duplicate filtering
- Supports optional pre-translation subtitle cleanup
- Supports overwrite/rename/skip when output files already exist

### Audio Transcription (ASR)
- Transcribes audio files to subtitles (wav, mp3, m4a, flac, ogg, wma)
- Downloads audio from YouTube videos
- Supports multiple Whisper models (tiny, base, small, medium, large)
- GPU acceleration (Metal, CUDA, HIP, Vulkan, OpenCL, CPU)
- Multiple output formats (SRT, TXT, JSON, Verbose)

## Development Status (as of 2026-03-14)

Implemented and working:
- SRT translation via Ollama chat completions
- Batch file import + duplicate filtering + drag-and-drop (tkinterdnd2)
- Translation options: cleanup, overwrite/rename/skip, backup on replace
- ASR transcription via whisper.cpp (local models)
- YouTube audio download (yt-dlp) and audio conversion pipeline
- GPU backends with graceful CPU fallback
- Multiple output formats (SRT/TXT/JSON/Verbose)
- uv-first workflow with pip fallback

In progress / next focus:
- Unify legacy subtitle translation thread into the coordinator path
- UI copy and language consistency cleanup
- Packaging for macOS/Windows (PyInstaller specs exist)
- Expand test coverage for GUI + ASR edge cases

## Prerequisites

- Python 3.10+
- Ollama running locally (`http://localhost:11434`) - for translation only
- At least one chat model available in Ollama

Optional:
- `tkinterdnd2` for drag-and-drop support (already included in `requirements.txt`)

For ASR, the project includes:
- `whisper.cpp/` - Complete whisper.cpp library (226 MB)
- Pre-built libwhisper.dylib for macOS
- Test Whisper models

## Install (Recommended: uv)

```bash
uv sync
```

Fallback (pip + requirements.txt):

```bash
pip install -r requirements.txt
```

## Start Ollama and Pull a Model (for Translation)

```bash
ollama serve
ollama pull gpt-oss:20b
```

You can use a different model if it supports Ollama's chat completions API.

## Run the App

Recommended:

```bash
uv run python main.py
```

Fallback:

```bash
python main.py
```

## Develop Mode Logging

Enable verbose development logs with either environment variable:

```powershell
$env:APP_ENV="development"; uv run python main.py
```

```powershell
$env:APP_DEBUG="1"; uv run python main.py
```

Default mode stays at `INFO` log level.

## First Translation in 5 Steps

1. Switch to the **Translation** tab.
2. Click `Select SRT Files` or `Add Folder`.
3. Choose `Source Language` and `Target Language`.
4. Select a model from the model dropdown (requires Ollama running).
5. Set `Parallel Requests` (start with `3-5` if your machine is modest).
6. Click `Start Translation`.

## First Audio Transcription in 5 Steps

1. Switch to the **ASR (Audio Transcription)** tab.
2. Click `Select Audio File` and choose your audio file, OR enter a YouTube URL and click `Download from YouTube`.
3. Select Whisper model path (default: `whisper.cpp/models/ggml-base.bin`).
4. Enable `Use GPU Acceleration` and select GPU backend (e.g., `metal` for macOS).
5. Choose transcription language and output format (SRT recommended).
6. Click `Start Transcription`.

## Key Options

### Translation Tab
- `Auto Clean Before Translation`: Removes bracket-only subtitle lines and reorders indices.
- `Replace Original File`: Writes output back to the original file path and creates a backup.
- `Clean Workspace After Translation`: Clears loaded files after completion.
- `Debug Mode`: Prints detailed translation traces to console.

### ASR Tab
- `Use GPU Acceleration`: Enables GPU acceleration for faster transcription.
- `GPU Backend`: Select GPU backend (auto, metal, cuda, hip, vulkan, opencl, cpu).
- `Transcription Language`: Choose language or auto-detect.
- `Output Format`: Choose SRT, TXT, JSON, or Verbose format.

## Output and Backup Rules

### Translation
- Default output adds a language suffix (example: `movie.zh_tw.srt`).
- If target file exists, you can choose `Overwrite`, `Rename`, or `Skip`.
- When `Replace Original File` is enabled, backups are stored in a `backup/` folder next to the source file.

### ASR Transcription
- Output file is saved to the specified path (default: `transcription.srt`).
- SRT format includes timestamps for each subtitle segment.
- TXT format contains plain text without timestamps.
- JSON format includes timing information and metadata.
- Verbose format shows start/end times for each segment.

## Quick Troubleshooting

### Translation
- Model list is empty:
  - Ensure `ollama serve` is running.
  - Confirm models exist: `ollama list`.
- Translation fails immediately:
  - Verify Ollama endpoint is reachable at `http://localhost:11434`.
  - Try a smaller model or lower parallel requests.

### ASR Transcription
- Whisper model not found:
  - Verify the model path points to a valid .bin file.
  - The project includes test models in `whisper.cpp/models/`.
- GPU acceleration not working:
  - Ensure your hardware supports the selected backend (e.g., Metal for Apple Silicon).
  - Try setting backend to `auto` or `cpu`.
- Transcription is slow:
  - Use a smaller model (tiny or base).
  - Enable GPU acceleration.
  - Increase thread count (in ASR coordinator code).

## Documentation

- Full technical docs (EN): [`docs/TECHNICAL.md`](docs/TECHNICAL.md)
- Full technical docs (ZH-TW): [`docs/TECHNICAL_ZH.md`](docs/TECHNICAL_ZH.md)
- Packaging notes: [`docs/packaging.md`](docs/packaging.md)

## License

MIT License. See [`LICENSE`](LICENSE).
