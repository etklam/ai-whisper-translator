# Single-Page ASR + Optional Translation Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the GUI into a single-page batch workflow that processes YouTube URLs and local audio files sequentially, runs ASR, and optionally runs translation via a checkbox (default off).

**Architecture:** Keep ASR on `ASRCoordinator` and wire a new queue-based orchestrator inside the GUI. Use legacy `TranslationThread` for optional translation after ASR completes. Do not refactor translation coordinator in this iteration.

**Tech Stack:** Python 3.10+, Tkinter, existing ASR/whisper.cpp integration, legacy `TranslationThread`, uv/pytest.

---

### Task 1: Add queue data model and helpers in GUI

**Files:**
- Modify: `src/gui/app.py`

**Step 1: Write the failing test**

Add a minimal unit test for queue ordering and sequential dequeue (new test module):

```python
# tests/unit/presentation/test_queue_helpers.py
from src.gui.app import _build_source_queue

def test_build_source_queue_preserves_order():
    urls = ["https://a", "https://b"]
    files = ["/tmp/1.wav", "/tmp/2.wav"]
    queue = _build_source_queue(urls, files)
    assert [item["kind"] for item in queue] == ["url", "url", "file", "file"]
    assert [item["value"] for item in queue] == ["https://a", "https://b", "/tmp/1.wav", "/tmp/2.wav"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/presentation/test_queue_helpers.py -v`
Expected: FAIL (`_build_source_queue` not found or import error).

**Step 3: Write minimal implementation**

Add in `src/gui/app.py` (module-level helper):

```python
def _build_source_queue(urls, files):
    queue = []
    for url in urls:
        queue.append({"kind": "url", "value": url})
    for path in files:
        queue.append({"kind": "file", "value": path})
    return queue
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/presentation/test_queue_helpers.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_queue_helpers.py src/gui/app.py
git commit -m "test: add queue helper test"
```

---

### Task 2: Restructure UI into a single-page layout

**Files:**
- Modify: `src/gui/app.py`

**Step 1: Write the failing test**

Add/extend a UI smoke test asserting new widgets exist (by attribute):

```python
# tests/unit/presentation/test_single_page_ui.py
from src.gui.app import App


def test_single_page_widgets_exist():
    app = App(coordinator=None, asr_coordinator=None)
    assert hasattr(app, "url_text")
    assert hasattr(app, "select_audio_button")
    assert hasattr(app, "queue_list")
    assert hasattr(app, "enable_translation_var")
    app.destroy()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/presentation/test_single_page_ui.py -v`
Expected: FAIL (missing attributes).

**Step 3: Write minimal implementation**

Refactor `src/gui/app.py` to:
- Remove tabbed UI.
- Add single-page sections in order:
  - Sources (URL multi-line, multi-select audio button, queue list)
  - ASR settings
  - Translation settings (checkbox, default unchecked)
  - Output settings
  - Controls (start/stop/clear, progress)
- Create widget attributes referenced by tests.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/presentation/test_single_page_ui.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_single_page_ui.py src/gui/app.py
git commit -m "feat: refactor UI to single-page workflow"
```

---

### Task 3: Implement batch input for URLs and audio files

**Files:**
- Modify: `src/gui/app.py`

**Step 1: Write the failing test**

```python
# tests/unit/presentation/test_batch_input.py
from src.gui.app import _parse_urls


def test_parse_urls_strips_empty_lines():
    text = "\nhttps://a\n\nhttps://b\n"
    assert _parse_urls(text) == ["https://a", "https://b"]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/presentation/test_batch_input.py -v`
Expected: FAIL (`_parse_urls` missing).

**Step 3: Write minimal implementation**

Add in `src/gui/app.py`:

```python
def _parse_urls(text):
    return [line.strip() for line in text.splitlines() if line.strip()]
```

Wire UI:
- URL text box -> parse on start.
- Audio file button uses `askopenfilenames` and appends to queue list.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/presentation/test_batch_input.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_batch_input.py src/gui/app.py
git commit -m "feat: add batch URL/audio input"
```

---

### Task 4: Implement sequential queue execution (ASR only)

**Files:**
- Modify: `src/gui/app.py`

**Step 1: Write the failing test**

```python
# tests/unit/presentation/test_queue_execution.py
from src.gui.app import _build_source_queue


def test_queue_is_sequential():
    queue = _build_source_queue(["a", "b"], ["c"])
    assert queue[0]["value"] == "a"
    assert queue[1]["value"] == "b"
    assert queue[2]["value"] == "c"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/presentation/test_queue_execution.py -v`
Expected: FAIL (if helper not used or missing).

**Step 3: Write minimal implementation**

Add queue runner in `src/gui/app.py`:
- `self.queue_items` list
- `self.is_running` flag
- `start_queue()` builds queue and kicks `process_next()`
- `process_next()` pops next item, runs download if URL, then ASR via `ASRCoordinator` in background thread
- On completion, calls `process_next()`
- `stop_queue()` flips `is_running` to False

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/presentation/test_queue_execution.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_queue_execution.py src/gui/app.py
git commit -m "feat: add sequential queue execution"
```

---

### Task 5: Add optional translation step after ASR

**Files:**
- Modify: `src/gui/app.py`

**Step 1: Write the failing test**

```python
# tests/unit/presentation/test_translation_toggle.py
from src.gui.app import _should_translate


def test_should_translate():
    assert _should_translate(True) is True
    assert _should_translate(False) is False
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/presentation/test_translation_toggle.py -v`
Expected: FAIL (`_should_translate` missing).

**Step 3: Write minimal implementation**

Add helper in `src/gui/app.py`:

```python
def _should_translate(flag):
    return bool(flag)
```

Wire in queue pipeline:
- If enabled, after ASR writes SRT, spawn legacy `TranslationThread` using the ASR output path.
- Keep UI status updates for translation phase.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/presentation/test_translation_toggle.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_translation_toggle.py src/gui/app.py
git commit -m "feat: add optional translation step"
```

---

### Task 6: Add Stop/Clear Queue behavior and progress display

**Files:**
- Modify: `src/gui/app.py`

**Step 1: Write the failing test**

```python
# tests/unit/presentation/test_queue_controls.py
from src.gui.app import _queue_status_text


def test_queue_status_text():
    assert _queue_status_text(1, 3, "transcribing") == "1/3 - transcribing"
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/unit/presentation/test_queue_controls.py -v`
Expected: FAIL (`_queue_status_text` missing).

**Step 3: Write minimal implementation**

Add helper in `src/gui/app.py`:

```python
def _queue_status_text(current, total, status):
    return f"{current}/{total} - {status}"
```

Wire UI:
- Stop button sets `is_running = False` and updates status.
- Clear button clears queue list and resets progress.
- Progress label uses `_queue_status_text`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/unit/presentation/test_queue_controls.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_queue_controls.py src/gui/app.py
git commit -m "feat: add queue controls and status"
```

---

### Task 7: Manual validation checklist

**Files:**
- Modify: `docs/TECHNICAL.md`

**Step 1: Document manual validation**

Add a small section listing the 5 manual validation scenarios.

**Step 2: Commit**

```bash
git add docs/TECHNICAL.md
git commit -m "docs: add single-page workflow validation checklist"
```

---

## Notes / Known Issues
- Test runner currently fails due to `ModuleNotFoundError: src` unless `PYTHONPATH` is set; tests in this plan assume that will be resolved or tests are run with `PYTHONPATH=.`.
- Translation coordinator remains unchanged; legacy translation path is used for optional translation.
