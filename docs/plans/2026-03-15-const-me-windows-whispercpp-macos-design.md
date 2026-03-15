# Windows Const-me / macOS Whisper.cpp Design

## Goal

Use `Const-me/Whisper` as the ASR runtime on Windows while keeping `whisper.cpp` with Metal support on macOS.

## Scope

- Add a Windows-specific ASR provider for `Const-me/Whisper`.
- Keep macOS on the existing `whisper.cpp` integration path with Metal support.
- Route provider selection by platform through application and infrastructure boundaries.
- Keep the transcription output contract stable so UI and workflow code do not depend on the native backend.

## Current Constraints

- The current ASR path is built around a direct `whisper.cpp` ctypes wrapper in [`src/asr/whisper_wrapper.py`](/C:/Users/cas/Desktop/cmfile/Project/ai-whisper-translator/src/asr/whisper_wrapper.py) and [`src/asr/whisper_transcriber.py`](/C:/Users/cas/Desktop/cmfile/Project/ai-whisper-translator/src/asr/whisper_transcriber.py).
- Windows and macOS currently share the same native integration assumptions.
- Packaging scripts are oriented around `whisper.cpp` source checkout, build, and model download flows.
- `Const-me/Whisper` is Windows-only and does not provide a macOS Metal path.

## Recommended Approach

Introduce separate ASR providers per native runtime and choose them at the infrastructure boundary:

- `Windows -> ConstMeWhisperProvider`
- `macOS -> WhisperCppProvider`
- `auto` resolves to the platform default provider

The application layer should depend on a provider interface and common result model only. Native runtime loading, DLL/dylib path resolution, and provider-specific setup remain isolated inside infrastructure adapters.

## Architecture

### Provider Split

Keep `whisper.cpp` and `Const-me/Whisper` in separate adapters instead of merging both into one wrapper. This prevents platform-specific native APIs, loading logic, and error handling from accumulating in a single module.

### Resolver and Factory

Add provider selection logic that resolves:

- requested provider from config (`auto`, `whisper_cpp`, `const_me`)
- current platform (`win32`, `darwin`)
- platform/provider compatibility

The factory should create the concrete provider and reject unsupported combinations such as `macOS + const_me`.

### Stable Output Contract

Both providers should emit the same segment/result shape already expected by the workflow and output formatters. The UI and coordination code should not branch on provider type.

## Configuration

Add an `asr_provider` setting with these values:

- `auto`
- `whisper_cpp`
- `const_me`

Provider-specific settings remain scoped to the provider that uses them:

- `whisper.cpp`: `library_path`, `gpu_backend`, model path
- `Const-me`: runtime directory or DLL path, model path, and any Windows-only device/runtime options that are actually required

Validation rules:

- `auto` resolves to `const_me` on Windows and `whisper_cpp` on macOS
- `macOS + const_me` is invalid
- `Windows + whisper_cpp` can be rejected for now to keep the support surface narrow

## Packaging

### Windows

Replace the Windows setup/build flow that currently targets `whisper.cpp` with a `Const-me/Whisper` setup flow.

Runtime assets should live in a dedicated provider-specific location, for example:

- `runtime/asr/const-me/...`

This avoids mixing `Const-me` DLLs and models with `whisper.cpp` assets.

### macOS

Keep the current `whisper.cpp + Metal` packaging flow and store its assets separately, for example:

- `runtime/asr/whisper.cpp/...`

No macOS packaging changes should assume `Const-me` support.

## Error Handling

Normalize native failures into application-level errors:

- provider load errors: missing DLL/dylib, incompatible runtime, missing dependencies
- model initialization errors: model file missing or unsupported
- transcription execution errors: audio conversion failure, native inference failure, empty output cases

Error messages should include the provider name and the failing runtime/model path so setup issues remain diagnosable.

## Testing Strategy

- Unit tests for provider resolution by platform and config
- Unit tests for provider factory validation of unsupported combinations
- Adapter tests for `Const-me` runtime path resolution and failure handling
- Regression tests that confirm coordinator/UI flows consume a provider-agnostic ASR result
- macOS regression coverage to ensure the existing `whisper.cpp + Metal` path remains intact

## Non-Goals

- Adding `Const-me/Whisper` support outside Windows
- Rewriting the entire ASR coordinator or UI flow
- Supporting every possible provider on every platform in this change
