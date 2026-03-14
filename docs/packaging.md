# Packaging Notes

This repo includes packaging placeholders and helper scripts.

## Supported Entry Points

- Installed script: `ai-whisper-translator`
- Source dev command: `uv run ai-whisper-translator`
- Thin wrappers: `python main.py` or `python -m src.main`

## Specs

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

## Build whisper.cpp Shared Library

### macOS

```bash
chmod +x packaging/macos/build-whisper-cpp.sh
./packaging/macos/build-whisper-cpp.sh --backend metal
./packaging/macos/build-whisper-cpp.sh --backend cpu
```

### Windows

```powershell
./packaging/windows/build-whisper-cpp.ps1
```

## Onboarding (macOS)

```bash
chmod +x packaging/macos/onboarding-whisper-cpp.sh
./packaging/macos/onboarding-whisper-cpp.sh
```

Options:
- `--no-model` skip model download
- `--native true` enable native CPU optimizations

## Runtime Backend Priority

- Windows: `cuda → hip → vulkan → cpu`
- macOS (Apple Silicon): `metal → cpu`
- Other: `cpu`

## Runtime Assumptions

- Startup performs no package installation or environment mutation.
- Remote OpenAI-compatible endpoints are disabled unless `ALLOW_REMOTE_AI_ENDPOINTS=1`.
- API keys are not persisted into `.config`.
