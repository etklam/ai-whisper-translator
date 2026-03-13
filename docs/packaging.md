# Packaging Profiles

This project now defines packaging profile placeholders for:

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

Windows build helper:

- `packaging/windows/build-whisper-cpp.ps1` (builds `whisper.dll` into `whisper.cpp/build/src/`)

macOS build helper:

- `packaging/macos/build-whisper-cpp.sh` (builds `libwhisper.dylib` into `whisper.cpp/build/src/`)
- If first run fails with permission, make it executable:
  - `chmod +x packaging/macos/build-whisper-cpp.sh`

Runtime backend priority is represented in `RuntimeManifest`:

- Windows: `cuda -> hip -> vulkan -> cpu`
- macOS (Apple Silicon): `metal_coreml -> cpu`
- Other platforms: `cpu`

These profiles establish the contract for future runtime bundle integration.
