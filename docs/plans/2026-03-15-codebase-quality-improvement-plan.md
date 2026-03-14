# Codebase Quality Improvement Plan

Date: 2026-03-15

## Executive Summary

Current codebase quality is acceptable for a single-developer desktop app, but it is not in a good long-term state.

- Maintainability: 4/10
- Stability: 6/10
- Security: 4/10

The main reason is not lack of functionality. The main reason is inconsistent architecture. The repository already has a cleaner coordinator-based path, but the runtime still depends on a very large Tkinter file, a legacy translation thread, duplicated workflow logic, and unsafe operational defaults.

## Evidence-Based Assessment

### Maintainability

Strengths:
- The repository has a visible layered direction: `application`, `domain`, `infrastructure`.
- Coordinator-level code is materially cleaner than the legacy path.
- Unit tests exist and currently pass (`24 passed, 1 skipped` on 2026-03-15).

Weaknesses:
- GUI composition, state, workflow orchestration, config persistence, and localization are concentrated in [`src/gui/app.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/gui/app.py), which is about 2994 lines.
- Legacy translation flow remains active through [`src/translation/translation_thread.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/translation/translation_thread.py), while newer logic exists in [`src/application/translation_coordinator.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/application/translation_coordinator.py). That means two execution models must be maintained.
- The runtime still relies on bootstrapping shortcuts such as `sys.path.append(...)` in [`src/main.py#L7`](/Users/klam/Desktop/project/ai-whisper-translator/src/main.py#L7).
- There is still top-level environment mutation in [`main.py#L4`](/Users/klam/Desktop/project/ai-whisper-translator/main.py#L4).

Assessment:
- The code is understandable in parts, but change cost is too high.
- Most future regressions will come from hidden coupling in the GUI and from keeping old and new flows alive at the same time.

### Stability

Strengths:
- Coordinators have basic summaries, retries, and structured event callbacks.
- Existing tests cover several coordinator, infrastructure, and GUI guard behaviors.
- Recent bug-fix documentation suggests critical runtime issues were addressed.

Weaknesses:
- The ASR and translation flows are still split between coordinator-based orchestration and thread-driven legacy behavior.
- [`src/translation/translation_thread.py#L75`](/Users/klam/Desktop/project/ai-whisper-translator/src/translation/translation_thread.py#L75) creates its own event loop inside a worker thread and mixes async and sync work in a fragile way.
- [`src/translation/translation_thread.py#L229`](/Users/klam/Desktop/project/ai-whisper-translator/src/translation/translation_thread.py#L229) blocks indefinitely on `queue.get()` while waiting for UI conflict handling.
- File processing and backup logic are duplicated across [`src/application/translation_coordinator.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/application/translation_coordinator.py), [`src/translation/translation_thread.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/translation/translation_thread.py), and [`src/utils/file_utils.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/utils/file_utils.py).
- Stability claims are limited by test scope. There are no end-to-end tests for download -> ASR -> translation -> output persistence.

Assessment:
- The current build is test-passing, but runtime stability still depends heavily on careful operator behavior and untested integration paths.

### Security

Strengths:
- Subprocess usage mostly avoids `shell=True`.
- Translation clients at least centralize outbound HTTP handling.

Weaknesses:
- [`src/main.py#L22`](/Users/klam/Desktop/project/ai-whisper-translator/src/main.py#L22) automatically runs `pip install --upgrade yt-dlp` at startup. That is a supply-chain and operational safety problem, not just a UX issue.
- [`src/gui/app.py#L2838`](/Users/klam/Desktop/project/ai-whisper-translator/src/gui/app.py#L2838) persists `openai_api_key` into the local `.config` file in plain text.
- Endpoint and API key handling are spread across GUI fields, environment variables, and client defaults without a clear trust model.
- Output paths, backup paths, and user-provided file locations do not appear to go through a centralized validation layer.
- The app opens user directories via subprocess from the GUI path, which is low risk by itself, but it reinforces the lack of a consolidated boundary for local side effects.

Assessment:
- No obvious critical RCE pattern was found, but secret handling and startup package mutation are below a reasonable baseline.

## Target State

The target is a single execution path per feature, explicit boundaries for IO and secrets, and test coverage focused on real workflows instead of only unit behavior.

Definition of done:
- One translation execution path.
- GUI reduced to presentation and state binding, not business workflow.
- No automatic package installation during app startup.
- No plaintext API key persistence in repo-local config.
- End-to-end tests cover the main happy path and key failure paths.

## Improved Plan

### Phase 0: Freeze Risky Behavior

Goal:
- Remove the highest-risk behavior before broader refactoring.

Tasks:
- Remove automatic `pip install --upgrade yt-dlp` from startup in [`src/main.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/main.py).
- Replace it with an explicit user-triggered dependency check or a packaging-time install/update step.
- Stop persisting `openai_api_key` in `.config` from [`src/gui/app.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/gui/app.py).
- Add a migration path: if a plaintext key exists in old config, warn once and delete it after successful import to environment or OS keychain.

Acceptance criteria:
- App startup performs no network/package mutation.
- No new plaintext secrets are written to disk.
- Existing users do not lose access silently; they get a clear migration notice.

### Phase 1: Collapse to One Translation Runtime

Goal:
- Eliminate architectural duplication and reduce regression surface.

Tasks:
- Define `TranslationCoordinator` as the only translation execution path.
- Move conflict-resolution policy, backup policy, and output naming behind coordinator-facing interfaces.
- Retire [`src/translation/translation_thread.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/translation/translation_thread.py) after all call sites are migrated.
- Add an adapter if the GUI still needs async behavior, but keep the thread wrapper thin and coordinator-driven.

Acceptance criteria:
- No production workflow directly depends on `TranslationThread`.
- Translation logic exists in one place only.
- Backup and output-path rules are implemented once.

### Phase 2: Break Up the Tkinter Monolith

Goal:
- Reduce change cost and isolate UI regressions.

Tasks:
- Split [`src/gui/app.py`](/Users/klam/Desktop/project/ai-whisper-translator/src/gui/app.py) into focused modules:
  - `gui/views/translation_panel.py`
  - `gui/views/asr_panel.py`
  - `gui/views/ai_settings_panel.py`
  - `gui/presenters/app_controller.py`
  - `gui/config/settings_store.py`
- Extract translation dictionaries into resource files instead of embedding them inside the root window class.
- Move queue state and status formatting into dedicated presenter/state objects.
- Keep Tkinter widgets dumb: read state, emit intents, render results.

Acceptance criteria:
- No single GUI file exceeds roughly 500 to 700 lines.
- UI tests can target presenter/state behavior without instantiating the full app.
- Localization changes do not require editing the root app class.

### Phase 3: Create Explicit Security and Configuration Boundaries

Goal:
- Make secrets, endpoints, and filesystem side effects predictable.

Tasks:
- Introduce a typed settings object for endpoint, model, output, and GPU options.
- Separate secret sources from normal settings. Prefer environment variables or OS keychain for API keys.
- Validate and normalize all user-controlled paths before use.
- Add an allowlist model for external endpoints if the app is intended to remain local-first.
- Review logging to ensure API keys, auth headers, and sensitive prompts are never written.

Acceptance criteria:
- Secret values are not persisted in plaintext config.
- All filesystem writes go through one validation layer.
- External service configuration is explicit and documented.

### Phase 4: Raise Integration Stability

Goal:
- Test the workflows that actually break in production.

Tasks:
- Add integration tests for:
  - SRT clean + translate + save
  - Replace-original with backup creation
  - Download failure does not stop queue
  - ASR failure emits correct summary
  - Translation failure preserves ASR output and reports partial failure clearly
- Add contract tests for translation clients and subtitle repository behavior.
- Add one smoke test for app startup with external dependencies mocked.

Acceptance criteria:
- Happy path and major failure paths are covered by automated tests.
- The team can refactor coordinator or GUI wiring without relying on manual regression checking.

### Phase 5: Normalize Entry Points and Packaging

Goal:
- Make runtime behavior deterministic across development and packaged builds.

Tasks:
- Remove `sys.path` manipulation from [`src/main.py#L7`](/Users/klam/Desktop/project/ai-whisper-translator/src/main.py#L7).
- Replace top-level environment mutation in [`main.py`](/Users/klam/Desktop/project/ai-whisper-translator/main.py) with config-driven defaults.
- Document one supported startup path for development and one for packaged distribution.
- Ensure bundled `whisper.cpp` integration has a clear ownership boundary so app code does not depend on repo layout accidents.

Acceptance criteria:
- There is one documented entrypoint per runtime mode.
- Startup does not depend on ad hoc path hacking.
- Packaging docs match actual runtime behavior.

## Priority Order

Implementation order:
1. Phase 0
2. Phase 1
3. Phase 3
4. Phase 2
5. Phase 4
6. Phase 5

Reasoning:
- Phase 0 and Phase 3 remove the largest safety risks.
- Phase 1 removes the largest maintenance and stability multiplier.
- Phase 2 becomes much safer after the runtime path is unified.
- Phase 4 should validate the refactor as it lands.

## Non-Goals

These items should not be mixed into the same refactor unless they block a phase:
- Rewriting the app away from Tkinter
- Replacing `urllib` with another HTTP library just for style
- Large UI redesign
- Full cross-platform packaging overhaul in the first pass

## Recommended First Milestone

The first milestone should be a short hardening release:

- Remove startup auto-update of `yt-dlp`
- Stop storing API keys in `.config`
- Route all translation through `TranslationCoordinator`
- Add integration tests for replace-original, retry/failure, and output generation

If that milestone is complete, the codebase quality should move roughly to:

- Maintainability: 6/10
- Stability: 7/10
- Security: 7/10
