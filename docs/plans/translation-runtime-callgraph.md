# Translation Runtime Callgraph

Date: 2026-03-15

## Active Production Paths

### GUI direct translation

1. `src/gui/app.py:start_translation()`
2. `src/gui/presenters/clean_workflow.py:run_clean_workflow()` when pre-clean is enabled
3. `src/gui/presenters/translation_runner.py:build_translation_request()`
4. `src/gui/presenters/translation_runner.py:run_translation_request()`
5. `src/application/translation_coordinator.py:run_async()`
6. `src/application/translation_coordinator.py:run()`

Status: coordinator path

### Queue translation after ASR

1. `src/gui/presenters/queue_execution.py:run_queue_item()`
2. `src/gui/presenters/queue_execution.py:run_translation_for_output()`
3. `src/gui/app.py:_start_translation_request()`
4. `src/gui/presenters/translation_runner.py:build_translation_request()`
5. `src/gui/presenters/translation_runner.py:run_translation_request()`
6. `src/application/translation_coordinator.py:run_async()`
7. `src/application/translation_coordinator.py:run()`

Status: coordinator path

## Removed Path

### Legacy thread runtime

- Removed: `src/translation/translation_thread.py`
- Previous role: translation batching, file conflict UI, backup handling
- Replacement: coordinator + presenter-based UI updates

Status: retired
