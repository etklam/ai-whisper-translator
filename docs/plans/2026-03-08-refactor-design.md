# Refactor Design: Reliability, Testability, and Extensibility
Date: 2026-03-08
Project: srt-subtitle-translator-enhanced

## 1. Goals and Priorities
User priorities:
- Primary: B (stability/reliability), then A (clear architecture), then C (technology direction consistency).
- Change policy: B + C (bug fixes allowed; moderate behavior and flow improvements allowed).
- Acceptance focus: A + B (testability and operational reliability).

## 2. Scope and Non-Goals
In scope:
- Refactor translation execution flow (threading/concurrency/API reliability).
- Refactor file handling flow (SRT read/write/backup/clean/output naming/conflicts).
- Refactor GUI coupling (UI decoupled from orchestration and domain logic).
- Introduce ASR extension points for future whisper.cpp integration.

Out of scope for this iteration:
- Full technology migration from Python to TypeScript.
- Cross-platform one-shot packaging pipeline producing all OS artifacts from one build.

## 3. Considered Approaches
### Approach 1: Incremental Layering (Low Risk)
- Keep current Tkinter + thread model and gradually extract logic.
- Pros: safest behavior parity.
- Cons: limited reliability gains in orchestration and failure handling.

### Approach 2: Coordinator-Centric Refactor (Recommended)
- Introduce `TranslationCoordinator` as orchestration boundary.
- UI subscribes to events; services become injectable and testable.
- Pros: best balance for reliability, testability, and medium-size changes.
- Cons: moderate refactor complexity.

### Approach 3: Clean-Architecture Rebuild (High Risk)
- Full domain-first redesign with adapters for GUI/CLI/future TS.
- Pros: strongest long-term flexibility.
- Cons: highest delivery and regression risk.

Decision: **Approach 2**.

## 4. Target Architecture
Directory intent:
- `presentation/gui`: Tkinter UI only (events, rendering, dialogs).
- `application/coordinator`: workflow orchestration, progress, retries, summaries.
- `domain/services`: business interfaces and policies.
- `infrastructure/*`: concrete adapters (pysrt, urllib/http, filesystem, whisper binaries).

Core contracts:
- `TranslationCoordinator.start(request)`
- `TranslationClient.translate_batch(...)`
- `SubtitleRepository.read/write/clean/backup/resolve_output(...)`
- `PromptProvider.get_prompt(mode)`

UI responsibilities:
- Collect user input.
- Display progress and conflict dialogs.
- No direct API calls or file business logic.

## 5. Data Flow and Error Handling
### Data Flow
1. UI builds `TranslationRequest` and calls coordinator.
2. Coordinator validates request and emits startup status.
3. Optional clean phase via `SubtitleRepository.clean(...)` with progress events.
4. Translation phase by file and subtitle batch.
5. Save phase with conflict policy (`overwrite` / `rename` / `skip`).
6. Final execution summary emitted.

### Error Strategy
Error classes:
- `ValidationError`
- `ExternalServiceError`
- `FileOperationError`
- `ConflictResolutionError`

Policies:
- Subtitle-level failure: retry N times (default 1), then mark failed and continue.
- File-level failure: continue remaining files.
- Batch-level completion always produces summary:
  - success count
  - partial failure count
  - failed count
  - key errors list

Coordinator emits events; GUI decides visual presentation (`messagebox`, status text, log panel).

## 6. Testing Strategy (Acceptance A/B)
### Unit Tests
- `PromptProvider`: normal load, missing file fallback, malformed JSON fallback.
- `SubtitleRepository`: naming rules, language suffix, replace-original mode, backup behavior, clean rules.
- `TranslationClient`: success parse, timeout, transport error, invalid payload.

### Coordinator Tests
- Ordered progress events for multi-file and multi-batch flows.
- Retry then success path.
- Retry exhausted path with continuation.
- File conflict paths: overwrite/rename/skip.
- One file failure does not abort whole queue.

### Integration Tests
- End-to-end with fake translation backend.
- Verify output content, per-file outcomes, and final summary consistency.

Acceptance criteria:
- All critical-path tests pass.
- Failure scenarios are observable and non-catastrophic.
- Batch job completes with deterministic final report.

## 7. Migration Plan
### Phase 1: Testable Foundations
- Extract `PromptProvider`, `SubtitleRepository`, `TranslationClient` from monolithic code.
- Add unit tests and fixed fixtures.

### Phase 2: Coordinator Introduction
- Implement `TranslationCoordinator` and migrate current translation workflow.
- UI moves to event-driven interaction.

### Phase 3: Reliability Hardening
- Add retry policy, structured errors, and execution summary.
- Add coordinator and integration tests.

### Phase 4: Structural Cleanup and Future C
- Normalize module boundaries (`presentation/application/domain/infrastructure`).
- Keep TypeScript artifacts as future integration targets, not active migration scope now.

## 8. Future ASR Extension: whisper.cpp Backends
Target policy (approved): **GPU first, CPU fallback; support AMD and macOS (Apple Silicon only)**.

### ASR Abstractions
- `ASRProvider.transcribe(input) -> segments`
- `BackendResolver` for runtime capability detection and backend selection.

### Planned backend order
- Windows: `CUDA -> HIP/ROCm (if available) -> Vulkan -> CPU`
- macOS (Apple Silicon): `Metal/CoreML -> CPU`

Fallback behavior:
- Any backend initialization or runtime failure triggers automatic degrade to next backend.
- Coordinator receives degrade events and records them in execution summary/logs.

## 9. Packaging Strategy
- Separate build profiles:
  - `windows-exe`
  - `macos-app` (Apple Silicon)
- Ship whisper.cpp runtime assets as managed external bundle per profile.
- Keep backend/runtime metadata in a manifest file used by resolver.

## 10. Risks and Mitigations
- Risk: regression during UI decoupling.
  - Mitigation: introduce coordinator behind stable UI interfaces and cover with coordinator tests first.
- Risk: backend availability variance across machines.
  - Mitigation: capability detection + explicit fallback chain + observable degrade logs.
- Risk: packaging complexity on macOS.
  - Mitigation: dedicated mac profile and staged signing/notarization tasks.

## 11. Design Decision Summary
- Architecture baseline: Coordinator-centric layered refactor.
- Immediate priorities: testability and reliability.
- Extension-ready for whisper.cpp with multi-backend fallback policy.
- Platform targets: Windows first, macOS Apple Silicon supported in dedicated profile.
