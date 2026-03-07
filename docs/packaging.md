# Packaging Profiles

This project now defines packaging profile placeholders for:

- `packaging/windows/pyinstaller.spec`
- `packaging/macos/pyinstaller.spec`

Runtime backend priority is represented in `RuntimeManifest`:

- Windows: `cuda -> hip -> vulkan -> cpu`
- macOS (Apple Silicon): `metal_coreml -> cpu`
- Other platforms: `cpu`

These profiles establish the contract for future runtime bundle integration.
