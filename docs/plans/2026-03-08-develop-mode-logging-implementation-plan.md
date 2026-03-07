# Develop Mode Logging Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add environment-driven develop mode with centralized logging and broad debug instrumentation across core runtime paths.

**Architecture:** Introduce a runtime logging config module and initialize it at startup before any application objects. Instrument key modules with module-level loggers and debug/info calls while preserving existing behavior.

**Tech Stack:** Python `logging`, `pytest`, environment variables (`APP_ENV`, `APP_DEBUG`).

---

### Task 1: Add logging runtime module with tests (TDD)

**Files:**
- Create: `tests/unit/infrastructure/runtime/test_logging_config.py`
- Create: `src/infrastructure/runtime/logging_config.py`

**Step 1: Write failing tests for environment detection and level selection**
- assert `APP_ENV=development` enables develop mode
- assert `APP_DEBUG=1` enables develop mode
- assert default env is not develop mode
- assert configure function sets expected root level

**Step 2: Run targeted tests to verify failure**
Run: `uv run pytest tests/unit/infrastructure/runtime/test_logging_config.py -v`
Expected: FAIL (module/function missing)

**Step 3: Implement minimal logging config module**
- implement `is_develop_mode`
- implement `configure_logging`
- return boolean mode from `configure_logging`

**Step 4: Re-run targeted tests**
Run: `uv run pytest tests/unit/infrastructure/runtime/test_logging_config.py -v`
Expected: PASS

### Task 2: Wire startup logging initialization

**Files:**
- Modify: `src/main.py`

**Step 1: Add logger and initialize logging in `main()`**
- call `configure_logging()` at startup
- log mode and initialization milestones

**Step 2: Run affected test**
Run: `uv run pytest tests/unit/presentation/test_app_event_binding.py -v`
Expected: PASS

### Task 3: Instrument coordinator and infrastructure modules

**Files:**
- Modify: `src/application/translation_coordinator.py`
- Modify: `src/infrastructure/translation/ollama_translation_client.py`
- Modify: `src/infrastructure/prompt/json_prompt_provider.py`
- Modify: `src/utils/file_utils.py`

**Step 1: Add module loggers and debug/info/error events**
- add per-file processing and retry logs in coordinator
- add request/response/error logs in client
- add prompt load/fallback logs
- add backup/cleanup/output-path logs

**Step 2: Run targeted tests for these modules**
Run:
- `uv run pytest tests/unit/application/test_translation_coordinator.py -v`
- `uv run pytest tests/unit/infrastructure/test_ollama_translation_client.py -v`
- `uv run pytest tests/unit/domain/test_prompt_provider.py -v`
- `uv run pytest tests/unit/infrastructure/test_pysrt_subtitle_repository.py -v`
Expected: PASS

### Task 4: Instrument GUI and translation thread paths

**Files:**
- Modify: `src/gui/app.py`
- Modify: `src/translation/translation_thread.py`

**Step 1: Add debug logs at key user and batch events**
- file selection/folder import summaries
- translation start request summaries
- conflict decisions and completion updates
- thread batch and save lifecycle

**Step 2: Run impacted presentation test**
Run: `uv run pytest tests/unit/presentation/test_app_event_binding.py -v`
Expected: PASS

### Task 5: Final verification

**Files:**
- Verify changed files

**Step 1: Run focused suite**
Run:
- `uv run pytest tests/unit/infrastructure/runtime/test_logging_config.py -v`
- `uv run pytest tests/unit/application/test_translation_coordinator.py -v`
- `uv run pytest tests/unit/infrastructure/test_ollama_translation_client.py -v`
- `uv run pytest tests/unit/domain/test_prompt_provider.py -v`
- `uv run pytest tests/unit/presentation/test_app_event_binding.py -v`
- `uv run pytest tests/unit/test_smoke.py -v`

Expected: all PASS

**Step 2: Inspect working tree**
Run: `git status --short`
Expected: only intended files modified
