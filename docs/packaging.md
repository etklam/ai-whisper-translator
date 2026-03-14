# Packaging Notes

This repo includes packaging placeholders and helper scripts.

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
