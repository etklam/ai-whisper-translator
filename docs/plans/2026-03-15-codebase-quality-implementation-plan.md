# Codebase Quality Implementation Plan

Date: 2026-03-15

**Goal:** Improve the codebase in a way that materially raises maintainability, stability, and security without disrupting the current working desktop app.

**Strategy:** Execute a hardening-first refactor. Remove unsafe defaults first, collapse duplicated runtime paths second, then split the UI and strengthen testing around the real end-to-end workflows.

**Success Metrics:**
- No automatic package installation or network mutation during startup.
- No plaintext API key persistence in local config.
- Translation runtime uses one production path only.
- GUI orchestration logic is broken into smaller modules.
- Integration tests cover the main happy path and key failure paths.

---

## Phase 0: Hardening Baseline

### Task 0.1: Remove startup auto-update behavior

**Files:**
- Modify: `src/main.py`
- Modify: `README.md`
- Modify: `README_ZH.md`
- Optional create: `src/application/dependency_health.py`

**Problem:**
- [`src/main.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/main.py) currently runs `pip install --upgrade yt-dlp` during startup.

**Implementation steps:**
1. Delete `ensure_yt_dlp()` from app startup.
2. If dependency health checks are still needed, replace them with a pure validation function:
   - verify `yt_dlp` importability
   - return status/result object
   - do not mutate environment
3. Surface dependency issues as a GUI warning or startup log only.
4. Update README docs to explain how users update `yt-dlp` manually or through packaging flow.

**Acceptance criteria:**
- App startup performs no package installation.
- App startup performs no network activity caused by dependency bootstrap.
- Documentation reflects the new manual or packaged update flow.

**Suggested tests:**
- Add startup test asserting `subprocess.run` is not called from `main()`.

---

### Task 0.2: Stop storing API keys in `.config`

**Files:**
- Modify: `src/gui/app.py`
- Optional create: `src/gui/config/settings_store.py`
- Optional create: `tests/unit/presentation/test_settings_persistence.py`

**Problem:**
- `_collect_config()` currently serializes `openai_api_key` into config.

**Implementation steps:**
1. Remove `openai_api_key` from persisted config payload.
2. Keep endpoint and non-secret settings persisted.
3. Change config loading behavior:
   - if old config contains `openai_api_key`, detect it
   - warn once
   - do not write it back on next save
4. Read API key from environment variable or in-memory field only.
5. Ensure logs never print key contents.

**Acceptance criteria:**
- New config writes contain no API key field.
- Existing config with API key is tolerated but cleaned on next save.
- GUI still works when key is supplied via environment variable.

**Suggested tests:**
- Saving config omits `openai_api_key`.
- Loading old config does not crash and strips the secret on rewrite.

---

### Task 0.3: Add log redaction guardrails

**Files:**
- Modify: `src/infrastructure/runtime/logging_config.py`
- Modify: `src/infrastructure/translation/ollama_translation_client.py`
- Modify: `src/infrastructure/translation/libretranslate_client.py`
- Optional create: `tests/unit/infrastructure/test_logging_redaction.py`

**Problem:**
- Endpoint and auth handling are distributed. Future logging changes could leak secrets.

**Implementation steps:**
1. Define a small redaction helper for keys, bearer headers, and secret-like fields.
2. Ensure translation clients log endpoint/timeout only, never headers or full auth-bearing payloads.
3. Add a safe-logging convention in logging config or module helper.
4. Review existing debug logs for prompt and auth sensitivity.

**Acceptance criteria:**
- No API key or `Authorization` value is emitted in logs.
- Debug logging remains useful without exposing secrets.

---

## Phase 1: Unify Translation Runtime

### Task 1.1: Map all translation entry points

**Files:**
- Modify: `docs/TECHNICAL.md`
- Modify: `docs/TECHNICAL_ZH.md`
- Optional create: `docs/plans/translation-runtime-callgraph.md`

**Problem:**
- The repository currently has both coordinator-based and legacy-thread translation paths.

**Implementation steps:**
1. List all call sites that trigger subtitle translation.
2. Mark each one as:
   - coordinator path
   - legacy thread path
   - mixed path
3. Identify the minimum adapter needed to migrate GUI calls without rewriting the UI in one step.

**Acceptance criteria:**
- There is a documented migration map from old flow to new flow.
- No translation path is left implicit.

---

### Task 1.2: Move output conflict and backup policy into the coordinator path

**Files:**
- Modify: `src/application/translation_coordinator.py`
- Modify: `src/utils/file_utils.py`
- Optional create: `src/domain/services/output_policy.py`
- Optional create: `src/application/output_resolution.py`
- Add tests under: `tests/unit/application/`

**Problem:**
- Backup creation and output-path conflict logic are duplicated in `TranslationThread` and utility functions.

**Implementation steps:**
1. Define a single output policy abstraction:
   - replace original
   - skip if exists
   - overwrite if exists
   - rename if exists
2. Move filename generation and backup semantics out of legacy thread.
3. Make coordinator responsible for invoking this policy before save.
4. Ensure save behavior is deterministic and testable without GUI callbacks.

**Acceptance criteria:**
- Output path resolution lives in one production module.
- Replace-original and rename/skip/overwrite policies are unit-tested.
- Backup logic is not duplicated.

---

### Task 1.3: Replace `TranslationThread` with a thin async adapter

**Files:**
- Modify: `src/gui/app.py`
- Modify or create: `src/gui/presenters/translation_runner.py`
- Modify: `src/translation/translation_thread.py`
- Add tests under: `tests/unit/presentation/`

**Problem:**
- `TranslationThread` currently contains workflow logic, network invocation, file conflict coordination, and persistence.

**Implementation steps:**
1. Introduce a thin runner used by the GUI:
   - accepts a translation request
   - invokes `TranslationCoordinator.run()` in a worker thread
   - translates coordinator events into UI callbacks
2. Remove business logic from `TranslationThread`.
3. Either delete `TranslationThread` or keep it as a compatibility wrapper around the coordinator.
4. Migrate all GUI translation actions to the new runner.

**Acceptance criteria:**
- GUI no longer uses legacy translation logic directly.
- Translation behavior is identical for core user flows.
- `TranslationThread` no longer owns network + save + conflict handling.

**Suggested tests:**
- GUI runner dispatches request to coordinator.
- Completion and failure callbacks update UI state correctly.

---

### Task 1.4: Retire legacy translation implementation

**Files:**
- Delete or deprecate: `src/translation/translation_thread.py`
- Modify: `docs/TECHNICAL.md`
- Modify: `STRUCTURE.md`

**Implementation steps:**
1. Remove remaining imports/usages.
2. Delete file if no longer needed, or leave a minimal compatibility wrapper with deprecation note.
3. Update docs to reflect single-path architecture.

**Acceptance criteria:**
- No production call site depends on the old translation runtime.
- Structure docs no longer describe translation flow as split or temporary.

---

## Phase 2: Security and Configuration Boundary

### Task 2.1: Introduce typed settings models

**Files:**
- Create: `src/application/settings_models.py`
- Create: `src/gui/config/settings_store.py`
- Modify: `src/gui/app.py`
- Add tests under: `tests/unit/application/` and `tests/unit/presentation/`

**Problem:**
- Config is currently a loosely shaped dict assembled directly from widget state.

**Implementation steps:**
1. Define typed models for:
   - UI settings
   - translation settings
   - ASR settings
   - output settings
2. Add a settings store that:
   - loads raw JSON
   - validates/normalizes values
   - returns typed objects
   - writes only non-secret data
3. Convert GUI code from dict access to typed object access gradually.

**Acceptance criteria:**
- Config IO is centralized.
- Invalid config values are normalized or rejected predictably.
- GUI logic no longer directly owns config serialization format.

---

### Task 2.2: Add filesystem path validation

**Files:**
- Create: `src/application/path_validation.py`
- Modify: `src/application/asr_coordinator.py`
- Modify: `src/application/translation_coordinator.py`
- Modify: `src/asr/audio_downloader.py`
- Modify: `src/utils/file_utils.py`
- Add tests under: `tests/unit/application/`

**Problem:**
- User-controlled file paths and output paths are manipulated in multiple places without one guard layer.

**Implementation steps:**
1. Add helpers to validate:
   - input file exists and matches expected type
   - output directory exists or can be created
   - output path stays within intended location when using generated names
2. Normalize path handling to `pathlib.Path`.
3. Use the validator before backup, save, open-folder, and download-output operations.

**Acceptance criteria:**
- Coordinators reject invalid paths with structured errors.
- Path handling is consistent across ASR and translation flows.

---

### Task 2.3: Define trusted endpoint policy

**Files:**
- Modify: `src/infrastructure/translation/ollama_translation_client.py`
- Modify: `src/infrastructure/translation/libretranslate_client.py`
- Modify: `src/gui/app.py`
- Modify: `README.md`

**Problem:**
- Endpoint selection is flexible but undocumented and not clearly bounded.

**Implementation steps:**
1. Define the supported endpoint model:
   - local-only by default
   - explicit opt-in for remote endpoints
2. Enforce endpoint normalization and validation in one place.
3. Add user-facing warning for non-local endpoints if app is intended to be local-first.
4. Document trust assumptions.

**Acceptance criteria:**
- Endpoint behavior is explicit.
- Remote endpoint usage is intentional, not accidental.

---

## Phase 3: Break Up the GUI Monolith

### Task 3.1: Extract configuration persistence from `App`

**Files:**
- Create: `src/gui/config/settings_store.py`
- Modify: `src/gui/app.py`
- Add tests under: `tests/unit/presentation/`

**Implementation steps:**
1. Move `_collect_config`, `_apply_config`, load/save helpers into `settings_store.py`.
2. Keep `App` responsible only for mapping widget state to/from settings objects.
3. Reduce `App` knowledge of on-disk JSON shape.

**Acceptance criteria:**
- Config read/write code is removed from `App`.
- Config behavior is testable without initializing the full Tk app.

---

### Task 3.2: Extract localization resources

**Files:**
- Create: `src/gui/resources/translations.json`
- Modify: `src/gui/app.py`
- Optional create: `src/gui/resources/i18n.py`
- Add tests under: `tests/unit/presentation/`

**Problem:**
- Translation dictionaries are embedded in the 2994-line app class.

**Implementation steps:**
1. Move hardcoded language dictionaries into a resource file or dedicated module.
2. Add a loader with fallback behavior.
3. Keep only the active language state and UI update hooks in `App`.

**Acceptance criteria:**
- Language content no longer dominates the root app file.
- Missing keys fail safely with fallback text or controlled error.

---

### Task 3.3: Extract queue workflow state/presenter

**Files:**
- Create: `src/gui/presenters/queue_controller.py`
- Modify: `src/gui/app.py`
- Add tests under: `tests/unit/presentation/`

**Problem:**
- Queue state, processing flags, UI updates, and workflow transitions are tightly coupled to widget code.

**Implementation steps:**
1. Move queue operations into a presenter/controller:
   - build queue
   - start/stop
   - current item state
   - progress text
2. Keep `App` as a consumer of state changes.
3. Reuse presenter for both ASR-only and ASR+translation workflows.

**Acceptance criteria:**
- Queue logic is testable without Tk widgets.
- UI actions become thin intent handlers.

---

### Task 3.4: Split UI panels into focused modules

**Files:**
- Create: `src/gui/views/asr_panel.py`
- Create: `src/gui/views/translation_panel.py`
- Create: `src/gui/views/ai_settings_panel.py`
- Modify: `src/gui/app.py`

**Implementation steps:**
1. Extract widget construction per panel.
2. Pass in only required callbacks and state accessors.
3. Keep layout ownership simple and avoid overengineering.

**Acceptance criteria:**
- `src/gui/app.py` is reduced substantially.
- No single view module grows into a new monolith.

---

## Phase 4: Integration Stability

### Task 4.1: Add translation integration tests

**Files:**
- Create tests under: `tests/integration/translation/`

**Scenarios:**
- Clean SRT then translate and save.
- Replace-original creates backup before write.
- Retry succeeds after transient `ExternalServiceError`.
- Batch failure prevents partial corrupted save.

**Acceptance criteria:**
- Translation coordinator behavior is protected by integration tests, not just unit mocks.

---

### Task 4.2: Add ASR workflow integration tests

**Files:**
- Create tests under: `tests/integration/asr/`

**Scenarios:**
- ASR success emits expected summary and save path.
- ASR failure is surfaced as structured error.
- GPU fallback still reports actual runtime mode correctly.

**Acceptance criteria:**
- ASR orchestration regressions are caught without manual GUI testing.

---

### Task 4.3: Add queue-level workflow tests

**Files:**
- Create tests under: `tests/integration/presentation/`

**Scenarios:**
- URL download failure does not stop remaining queue items.
- Translation failure preserves ASR output and updates status correctly.
- Stop action prevents further queue processing.

**Acceptance criteria:**
- The main user workflow is covered as a system behavior.

---

### Task 4.4: Add startup smoke test

**Files:**
- Create: `tests/integration/test_startup_smoke.py`

**Scenarios:**
- Startup initializes coordinators and GUI bindings with all external side effects mocked.
- No startup subprocess/package installation occurs.

**Acceptance criteria:**
- Basic app boot path is under test.

---

## Phase 5: Normalize Entrypoints and Packaging

### Task 5.1: Remove path hacking from startup

**Files:**
- Modify: `src/main.py`
- Modify: `pyproject.toml`
- Optional create: package entry point metadata

**Implementation steps:**
1. Remove `sys.path.append(...)`.
2. Ensure package/module execution works through proper project packaging.
3. Define a single supported dev startup command.

**Acceptance criteria:**
- Startup works without import path mutation.

---

### Task 5.2: Remove environment mutation from root entrypoint

**Files:**
- Modify: `main.py`
- Modify: `src/main.py`

**Implementation steps:**
1. Stop mutating `OLLAMA_NUM_PARALLEL` at import time.
2. If a default is needed, resolve it through settings.
3. Make root `main.py` a pure thin wrapper or remove it if unnecessary.

**Acceptance criteria:**
- Importing the entrypoint has no side effects beyond import.

---

### Task 5.3: Align docs with real runtime

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `STRUCTURE.md`
- Modify: `docs/TECHNICAL.md`
- Modify: `docs/packaging.md`

**Implementation steps:**
1. Update runtime architecture docs to reflect the final single-path flow.
2. Document secret handling, endpoint policy, startup flow, and packaging assumptions.
3. Remove outdated references to temporary or legacy runtime choices.

**Acceptance criteria:**
- Docs describe the system that actually ships.

---

## Recommended Execution Order

Sprint 1:
1. Task 0.1
2. Task 0.2
3. Task 0.3
4. Task 4.4

Sprint 2:
1. Task 1.1
2. Task 1.2
3. Task 1.3
4. Task 1.4

Sprint 3:
1. Task 2.1
2. Task 2.2
3. Task 2.3

Sprint 4:
1. Task 3.1
2. Task 3.2
3. Task 3.3
4. Task 3.4

Sprint 5:
1. Task 4.1
2. Task 4.2
3. Task 4.3
4. Task 5.1
5. Task 5.2
6. Task 5.3

---

## Delivery Checklist

Before closing the whole initiative, verify:
- `uv run pytest -q` passes.
- New integration suites pass.
- Startup performs no implicit install/update behavior.
- Saving settings writes no plaintext secret.
- No production path imports or uses legacy translation logic.
- `src/gui/app.py` is materially smaller and no longer owns config persistence plus queue orchestration plus localization data.

## First Milestone Cut

If time is limited, ship this subset first:
- Task 0.1
- Task 0.2
- Task 1.2
- Task 1.3
- Task 4.1
- Task 4.4

That is the smallest slice that meaningfully improves all three dimensions:
- Maintainability: removes duplicated translation behavior
- Stability: protects the translation path with stronger tests
- Security: removes startup package mutation and plaintext secret persistence
