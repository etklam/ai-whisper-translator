# AI Whisper Translator (SRT) - Quick Start

Desktop GUI tool for translating `.srt` subtitle files with a local Ollama model.

Use this README for first-time setup and your first successful translation. For architecture and maintenance details, use the technical docs linked below.

## What It Does

- Translates one or many SRT files
- Supports drag-and-drop (when `tkinterdnd2` is installed)
- Supports folder import and duplicate filtering
- Supports optional pre-translation subtitle cleanup
- Supports overwrite/rename/skip when output files already exist

## Prerequisites

- Python 3.10+
- Ollama running locally (`http://localhost:11434`)
- At least one chat model available in Ollama

Optional:
- `tkinterdnd2` for drag-and-drop support (already included in `requirements.txt`)

## Install

```bash
pip install -r requirements.txt
```

## Start Ollama and Pull a Model

```bash
ollama serve
ollama pull gpt-oss:20b
```

You can use a different model if it supports Ollama's chat completions API.

## Run the App

```bash
python main.py
```

## First Translation in 5 Steps

1. Click `Select SRT Files` or `Add Folder`.
2. Choose `Source Language` and `Target Language`.
3. Select a model from the model dropdown.
4. Set `Parallel Requests` (start with `3-5` if your machine is modest).
5. Click `Start Translation`.

## Key Options

- `Auto Clean Before Translation`: Removes bracket-only subtitle lines and reorders indices.
- `Replace Original File`: Writes output back to the original file path and creates a backup.
- `Clean Workspace After Translation`: Clears loaded files after completion.
- `Debug Mode`: Prints detailed translation traces to console.

## Output and Backup Rules

- Default output adds a language suffix (example: `movie.zh_tw.srt`).
- If target file exists, you can choose `Overwrite`, `Rename`, or `Skip`.
- When `Replace Original File` is enabled, backups are stored in a `backup/` folder next to the source file.

## Quick Troubleshooting

- Model list is empty:
  - Ensure `ollama serve` is running.
  - Confirm models exist: `ollama list`.
- Translation fails immediately:
  - Verify Ollama endpoint is reachable at `http://localhost:11434`.
  - Try a smaller model or lower parallel requests.
- Drag-and-drop does not work:
  - Reinstall dependencies: `pip install -r requirements.txt`.

## Documentation

- Full technical docs (EN): [`docs/TECHNICAL.md`](docs/TECHNICAL.md)
- Full technical docs (ZH-TW): [`docs/TECHNICAL_ZH.md`](docs/TECHNICAL_ZH.md)
- Packaging notes: [`docs/packaging.md`](docs/packaging.md)

## License

MIT License. See [`LICENSE`](LICENSE).
