# Develop Mode Logging Design

## Context
The project has a Debug Mode UI option and scattered debug output, but no centralized environment-driven development logging behavior. The requirement is to enable large-volume debug logging via environment variables for development workflows.

## Goals
- Add environment-driven develop mode switch.
- Centralize logging configuration and format.
- Add broad debug logs across startup, GUI workflow, coordinator, translation client, prompt provider, file utilities, and legacy translation thread.
- Keep production/default behavior quiet at INFO level.

## Non-Goals
- No business logic rewrite.
- No protocol changes to Ollama integration.
- No removal of existing UI Debug Mode behavior (console text traces may remain as additional user-level debug).

## Trigger Rules
Develop mode enabled if either condition is true:
- `APP_ENV=development` (case-insensitive)
- `APP_DEBUG=1`

Otherwise, default logging level is INFO.

## Architecture
1. Add a runtime logging module under `src/infrastructure/runtime/logging_config.py`.
2. Expose utility functions:
   - `is_develop_mode(env: Mapping[str, str] | None = None) -> bool`
   - `configure_logging(env: Mapping[str, str] | None = None) -> bool`
3. `configure_logging` sets root logging level and stdout handler with unified formatter.
4. `src/main.py` calls `configure_logging()` before constructing coordinator and GUI.
5. All target modules use `logging.getLogger(__name__)` for structured logs.

## Logging Coverage
- Startup (`src/main.py`): mode detection, coordinator wiring.
- GUI (`src/gui/app.py`): file add/remove events, folder import stats, translation request summary, conflict decision path, completion summaries.
- Coordinator (`src/application/translation_coordinator.py`): file processing start/end, retries, final summary.
- Ollama client (`src/infrastructure/translation/ollama_translation_client.py`): outgoing request metadata, response parse status, error type.
- Prompt provider (`src/infrastructure/prompt/json_prompt_provider.py`): prompt path load success/fallback.
- File utilities (`src/utils/file_utils.py`): backup dir creation, cleanup counts, output path calculation.
- Translation thread (`src/translation/translation_thread.py`): batch boundaries, backup/save path, conflict flow.

## Reliability and Safety
- Do not log full subtitle content by default.
- Log counts, paths, options, and error classes/messages.
- Keep logging side effects non-blocking and tolerant to repeated initialization.

## Testing Strategy
- Add unit tests for develop-mode environment detection and logging config behavior.
- Add/adjust tests to ensure existing module behavior still passes with logging instrumentation.
- Run focused suite for changed areas plus smoke tests.

## Success Criteria
- `APP_ENV=development` or `APP_DEBUG=1` enables DEBUG logs.
- Default env remains INFO-level output.
- Updated modules emit debug logs without behavior regressions.
- Relevant tests pass.
