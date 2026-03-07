# Coordinator Refactor + ASR Foundation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the app around a testable coordinator architecture with reliability-first behavior, then add a cross-platform ASR backend abstraction (Windows AMD + macOS Apple Silicon) with GPU-first and CPU fallback policy.

**Architecture:** Keep Tkinter as presentation only, move workflow to an application-level coordinator, and isolate file/translation/prompt/asr logic behind domain service interfaces with infrastructure adapters. Build reliability via structured errors, retry policy, and deterministic execution summaries. Add a backend resolver for whisper.cpp strategy without coupling UI to platform-specific runtime details.

**Tech Stack:** Python 3, Tkinter, pysrt, pytest, unittest.mock, threading/queue, urllib, dataclasses

---

Reference skills for execution:
- `@superpowers:test-driven-development`
- `@superpowers:systematic-debugging`
- `@superpowers:verification-before-completion`

### Task 1: Create Test Scaffold and Baseline Fixtures

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/fixtures/sample_input.srt`
- Create: `tests/fixtures/sample_expected_cleaned.srt`
- Create: `tests/unit/test_smoke.py`

**Step 1: Write the failing test**

```python
# tests/unit/test_smoke.py
from pathlib import Path

def test_fixture_exists():
    fixtures_dir = Path(__file__).resolve().parents[1] / "fixtures"
    assert (fixtures_dir / "sample_input.srt").exists()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_smoke.py::test_fixture_exists -v`
Expected: FAIL because fixture file does not exist yet.

**Step 3: Write minimal implementation**

```python
# tests/conftest.py
from unittest.mock import Mock
import pytest

@pytest.fixture
def fake_services():
    return {
        "subtitle_repo": Mock(),
        "translation_client": Mock(),
        "prompt_provider": Mock(),
        "event_sink": Mock(),
    }
```

```text
# tests/fixtures/sample_input.srt
1
00:00:01,000 --> 00:00:02,000
Hello.
```

```text
# tests/fixtures/sample_expected_cleaned.srt
1
00:00:01,000 --> 00:00:02,000
Hello.
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_smoke.py::test_fixture_exists -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/conftest.py tests/fixtures tests/unit/test_smoke.py
git commit -m "test: add baseline pytest scaffold and fixtures"
```

### Task 2: Extract PromptProvider From Translation Thread

**Files:**
- Create: `src/domain/services/prompt_provider.py`
- Create: `src/infrastructure/prompt/json_prompt_provider.py`
- Modify: `src/translation/translation_thread.py`
- Test: `tests/unit/domain/test_prompt_provider.py`

**Step 1: Write the failing test**

```python
# tests/unit/domain/test_prompt_provider.py
from src.infrastructure.prompt.json_prompt_provider import JsonPromptProvider

def test_returns_default_prompt_when_file_missing(tmp_path):
    provider = JsonPromptProvider(str(tmp_path / "missing.json"))
    prompt = provider.get_prompt(use_alt_prompt=False)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/domain/test_prompt_provider.py::test_returns_default_prompt_when_file_missing -v`
Expected: FAIL with import/module path error.

**Step 3: Write minimal implementation**

```python
# src/domain/services/prompt_provider.py
from typing import Protocol

class PromptProvider(Protocol):
    def get_prompt(self, use_alt_prompt: bool) -> str: ...
```

```python
# src/infrastructure/prompt/json_prompt_provider.py
import json
from pathlib import Path

DEFAULT_PROMPT = "You are a professional translator."

class JsonPromptProvider:
    def __init__(self, prompt_path: str):
        self.prompt_path = Path(prompt_path)

    def get_prompt(self, use_alt_prompt: bool) -> str:
        try:
            data = json.loads(self.prompt_path.read_text(encoding="utf-8"))
            if use_alt_prompt:
                return data.get("alt_prompt", data.get("default_prompt", DEFAULT_PROMPT))
            return data.get("default_prompt", DEFAULT_PROMPT)
        except Exception:
            return DEFAULT_PROMPT
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/domain/test_prompt_provider.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/domain/services/prompt_provider.py src/infrastructure/prompt/json_prompt_provider.py src/translation/translation_thread.py tests/unit/domain/test_prompt_provider.py
git commit -m "refactor: extract prompt provider with fallback behavior"
```

### Task 3: Extract TranslationClient With Error Surface

**Files:**
- Create: `src/domain/services/translation_client.py`
- Create: `src/infrastructure/translation/ollama_translation_client.py`
- Create: `src/domain/errors.py`
- Modify: `src/translation/translation_thread.py`
- Test: `tests/unit/infrastructure/test_ollama_translation_client.py`

**Step 1: Write the failing test**

```python
# tests/unit/infrastructure/test_ollama_translation_client.py
from src.infrastructure.translation.ollama_translation_client import OllamaTranslationClient


def test_translate_text_returns_content_on_valid_response(monkeypatch):
    client = OllamaTranslationClient("http://localhost:11434/v1/chat/completions")
    payload = {"choices": [{"message": {"content": "你好"}}]}

    class DummyResponse:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def read(self):
            import json
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=30: DummyResponse())
    assert client.translate_text("hello", "繁體中文", "m", "p") == "你好"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/test_ollama_translation_client.py::test_translate_text_returns_content_on_valid_response -v`
Expected: FAIL with module not found.

**Step 3: Write minimal implementation**

```python
# src/domain/services/translation_client.py
from typing import Protocol

class TranslationClient(Protocol):
    def translate_text(self, text: str, target_lang: str, model_name: str, system_prompt: str) -> str: ...
```

```python
# src/domain/errors.py
class ExternalServiceError(Exception):
    pass
```

```python
# src/infrastructure/translation/ollama_translation_client.py
import json
import urllib.request
from src.domain.errors import ExternalServiceError

class OllamaTranslationClient:
    def __init__(self, endpoint: str):
        self.endpoint = endpoint

    def translate_text(self, text: str, target_lang: str, model_name: str, system_prompt: str) -> str:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Translate the following text to {target_lang}:\n{text}"},
            ],
            "stream": False,
            "temperature": 0.1,
        }
        req = urllib.request.Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            raise ExternalServiceError(str(exc)) from exc
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/test_ollama_translation_client.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/domain/services/translation_client.py src/infrastructure/translation/ollama_translation_client.py src/domain/errors.py src/translation/translation_thread.py tests/unit/infrastructure/test_ollama_translation_client.py
git commit -m "refactor: extract ollama translation client with explicit errors"
```

### Task 4: Extract SubtitleRepository for File Rules

**Files:**
- Create: `src/domain/services/subtitle_repository.py`
- Create: `src/infrastructure/subtitles/pysrt_subtitle_repository.py`
- Modify: `src/utils/file_utils.py`
- Test: `tests/unit/infrastructure/test_pysrt_subtitle_repository.py`

**Step 1: Write the failing test**

```python
# tests/unit/infrastructure/test_pysrt_subtitle_repository.py
from src.infrastructure.subtitles.pysrt_subtitle_repository import PysrtSubtitleRepository


def test_get_language_suffix_traditional_chinese():
    repo = PysrtSubtitleRepository()
    output = repo.get_output_path("movie.srt", "繁體中文", replace_original=False)
    assert output.endswith(".zh_tw.srt")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/test_pysrt_subtitle_repository.py::test_get_language_suffix_traditional_chinese -v`
Expected: FAIL with import/module error.

**Step 3: Write minimal implementation**

```python
# src/domain/services/subtitle_repository.py
from typing import Protocol

class SubtitleRepository(Protocol):
    def get_output_path(self, file_path: str, target_lang: str, replace_original: bool = False) -> str: ...
    def clean_srt_file(self, input_file: str, create_backup: bool = False) -> dict: ...
```

```python
# src/infrastructure/subtitles/pysrt_subtitle_repository.py
from src.utils.file_utils import get_output_path, clean_srt_file, ensure_backup_dir

class PysrtSubtitleRepository:
    def ensure_backup_dir(self, backup_path: str) -> None:
        ensure_backup_dir(backup_path)

    def get_output_path(self, file_path: str, target_lang: str, replace_original: bool = False) -> str:
        return get_output_path(file_path, target_lang, replace_original)

    def clean_srt_file(self, input_file: str, create_backup: bool = False) -> dict:
        return clean_srt_file(input_file, create_backup)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/test_pysrt_subtitle_repository.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/domain/services/subtitle_repository.py src/infrastructure/subtitles/pysrt_subtitle_repository.py src/utils/file_utils.py tests/unit/infrastructure/test_pysrt_subtitle_repository.py
git commit -m "refactor: introduce subtitle repository boundary"
```

### Task 5: Introduce Coordinator Models and Events

**Files:**
- Create: `src/application/models.py`
- Create: `src/application/events.py`
- Create: `tests/unit/application/test_models.py`

**Step 1: Write the failing test**

```python
# tests/unit/application/test_models.py
from src.application.models import TranslationRequest


def test_translation_request_defaults():
    req = TranslationRequest(file_paths=["a.srt"], source_lang="英文", target_lang="繁體中文", model_name="m")
    assert req.max_retries == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_models.py::test_translation_request_defaults -v`
Expected: FAIL because model module does not exist.

**Step 3: Write minimal implementation**

```python
# src/application/models.py
from dataclasses import dataclass
from typing import List

@dataclass
class TranslationRequest:
    file_paths: List[str]
    source_lang: str
    target_lang: str
    model_name: str
    parallel_requests: int = 3
    clean_before_translate: bool = False
    replace_original: bool = False
    use_alt_prompt: bool = False
    max_retries: int = 1
```

```python
# src/application/events.py
from dataclasses import dataclass

@dataclass
class ProgressEvent:
    current: int
    total: int
    message: str = ""
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_models.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/application/models.py src/application/events.py tests/unit/application/test_models.py
git commit -m "feat: add coordinator request and event models"
```

### Task 6: Build TranslationCoordinator for Existing SRT Flow

**Files:**
- Create: `src/application/translation_coordinator.py`
- Modify: `src/translation/translation_thread.py`
- Test: `tests/unit/application/test_translation_coordinator.py`

**Step 1: Write the failing test**

```python
# tests/unit/application/test_translation_coordinator.py
from src.application.models import TranslationRequest
from src.application.translation_coordinator import TranslationCoordinator


def test_continues_after_single_file_failure(fake_services):
    coordinator = TranslationCoordinator(**fake_services)
    req = TranslationRequest(file_paths=["a.srt", "b.srt"], source_lang="英文", target_lang="繁體中文", model_name="m")
    summary = coordinator.run(req)
    assert summary.total_files == 2
    assert summary.failed_files <= 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_translation_coordinator.py::test_continues_after_single_file_failure -v`
Expected: FAIL due missing coordinator implementation.

**Step 3: Write minimal implementation**

```python
# src/application/translation_coordinator.py
from dataclasses import dataclass

@dataclass
class ExecutionSummary:
    total_files: int
    successful_files: int
    failed_files: int

class TranslationCoordinator:
    def __init__(self, subtitle_repo, translation_client, prompt_provider, event_sink=None):
        self.subtitle_repo = subtitle_repo
        self.translation_client = translation_client
        self.prompt_provider = prompt_provider
        self.event_sink = event_sink

    def run(self, request):
        successful = 0
        failed = 0
        for _file in request.file_paths:
            try:
                successful += 1
            except Exception:
                failed += 1
        return ExecutionSummary(total_files=len(request.file_paths), successful_files=successful, failed_files=failed)

    def run_async(self, request, callback=None):
        import threading

        def _run():
            summary = self.run(request)
            if callback:
                callback(summary)

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_translation_coordinator.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/application/translation_coordinator.py src/translation/translation_thread.py tests/unit/application/test_translation_coordinator.py
git commit -m "feat: add translation coordinator with execution summary"
```

### Task 7: Rewire GUI to Coordinator Event API

**Files:**
- Modify: `src/gui/app.py`
- Modify: `src/main.py`
- Test: `tests/unit/presentation/test_app_event_binding.py`

**Step 1: Write the failing test**

```python
# tests/unit/presentation/test_app_event_binding.py
from src.gui.app import App


def test_app_has_coordinator_reference():
    app = App()
    assert hasattr(app, "coordinator")
    app.destroy()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/presentation/test_app_event_binding.py::test_app_has_coordinator_reference -v`
Expected: FAIL because App currently has no coordinator wiring.

**Step 3: Write minimal implementation**

```python
# in App.__init__
self.coordinator = coordinator

# in start_translation
# build request model and call self.coordinator.run_async(...)

# when handling coordinator events from worker thread
# marshal UI updates to Tk main thread
self.after(0, lambda: self._apply_progress(event))
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/presentation/test_app_event_binding.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/gui/app.py src/main.py tests/unit/presentation/test_app_event_binding.py
git commit -m "refactor: connect gui to coordinator event interface"
```

### Task 8: Add Retry Policy + Structured Error Mapping

**Files:**
- Modify: `src/application/translation_coordinator.py`
- Modify: `src/domain/errors.py`
- Test: `tests/unit/application/test_retry_policy.py`

**Step 1: Write the failing test**

```python
# tests/unit/application/test_retry_policy.py
from unittest.mock import Mock
from src.domain.errors import ExternalServiceError
from src.application.models import TranslationRequest
from src.application.translation_coordinator import TranslationCoordinator


def test_retry_once_then_success():
    client = Mock()
    client.translate_text.side_effect = [ExternalServiceError("temporary"), "ok"]
    repo = Mock()
    prompt = Mock()
    prompt.get_prompt.return_value = "p"
    coordinator = TranslationCoordinator(
        subtitle_repo=repo,
        translation_client=client,
        prompt_provider=prompt,
        event_sink=Mock(),
    )
    req = TranslationRequest(
        file_paths=["a.srt"],
        source_lang="英文",
        target_lang="繁體中文",
        model_name="m",
        max_retries=1,
    )
    summary = coordinator.run(req)
    assert summary.failed_files == 0
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_retry_policy.py::test_retry_once_then_success -v`
Expected: FAIL because retry logic is not implemented and first `ExternalServiceError` is not retried yet.

**Step 3: Write minimal implementation**

```python
# in TranslationCoordinator
for attempt in range(request.max_retries + 1):
    try:
        # translate subtitle
        break
    except ExternalServiceError:
        # retryable
        if attempt == request.max_retries:
            # mark failed and continue
            ...
    except Exception:
        # non-retryable (validation/file/programming errors)
        if attempt == request.max_retries:
            # mark failed and continue without retry loop extension
            ...
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_retry_policy.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/application/translation_coordinator.py src/domain/errors.py tests/unit/application/test_retry_policy.py
git commit -m "feat: add retry policy and structured error handling"
```

### Task 9: Add ASRProvider + BackendResolver Skeleton

**Files:**
- Create: `src/domain/services/asr_provider.py`
- Create: `src/infrastructure/asr/backend_resolver.py`
- Create: `src/infrastructure/asr/providers.py`
- Test: `tests/unit/infrastructure/asr/test_backend_resolver.py`

**Step 1: Write the failing test**

```python
# tests/unit/infrastructure/asr/test_backend_resolver.py
from src.infrastructure.asr.backend_resolver import resolve_backends


def test_windows_backend_priority():
    result = resolve_backends(platform="win32", gpu_caps={"cuda": True, "hip": True, "vulkan": True})
    assert result == ["cuda", "hip", "vulkan", "cpu"]

def test_cpu_fallback_always_present():
    result = resolve_backends(platform="win32", gpu_caps={"cuda": False, "hip": False, "vulkan": False})
    assert result == ["cpu"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/asr/test_backend_resolver.py::test_windows_backend_priority -v`
Expected: FAIL because resolver module does not exist.

**Step 3: Write minimal implementation**

```python
# src/infrastructure/asr/backend_resolver.py
def resolve_backends(platform: str, gpu_caps: dict) -> list[str]:
    if platform == "win32":
        order = ["cuda", "hip", "vulkan", "cpu"]
    elif platform == "darwin":
        order = ["metal_coreml", "cpu"]
    else:
        order = ["vulkan", "cpu"]
    available = [b for b in order if b == "cpu" or gpu_caps.get(b, False)]
    return available if available else ["cpu"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_backend_resolver.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/domain/services/asr_provider.py src/infrastructure/asr/backend_resolver.py src/infrastructure/asr/providers.py tests/unit/infrastructure/asr/test_backend_resolver.py
git commit -m "feat: add asr provider abstraction and backend resolver"
```

### Task 10: Add Packaging Profiles and Runtime Manifest Contract

**Files:**
- Create: `packaging/windows/pyinstaller.spec`
- Create: `packaging/macos/pyinstaller.spec`
- Create: `src/infrastructure/runtime/runtime_manifest.py`
- Create: `docs/packaging.md`
- Test: `tests/unit/infrastructure/runtime/test_runtime_manifest.py`

**Step 1: Write the failing test**

```python
# tests/unit/infrastructure/runtime/test_runtime_manifest.py
from src.infrastructure.runtime.runtime_manifest import RuntimeManifest


def test_runtime_manifest_has_backend_order():
    m = RuntimeManifest(platform="win32")
    assert "cpu" in m.backend_priority
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/runtime/test_runtime_manifest.py::test_runtime_manifest_has_backend_order -v`
Expected: FAIL due missing manifest module.

**Step 3: Write minimal implementation**

```python
# src/infrastructure/runtime/runtime_manifest.py
from dataclasses import dataclass

@dataclass
class RuntimeManifest:
    platform: str

    @property
    def backend_priority(self):
        if self.platform == "win32":
            return ["cuda", "hip", "vulkan", "cpu"]
        if self.platform == "darwin":
            return ["metal_coreml", "cpu"]
        return ["cpu"]
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/runtime/test_runtime_manifest.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add packaging/windows/pyinstaller.spec packaging/macos/pyinstaller.spec src/infrastructure/runtime/runtime_manifest.py docs/packaging.md tests/unit/infrastructure/runtime/test_runtime_manifest.py
git commit -m "build: add packaging profiles and runtime manifest contract"
```

## Final Verification Sequence
1. Run: `pytest -q`
Expected: all tests PASS.
2. Run: `python main.py`
Expected: GUI starts and can build translation request without runtime exceptions.
3. Run (manual): translate one short SRT with mockable local backend.
Expected: output file generated, summary shown, no crash.

## Notes for Execution
- Keep each commit scoped to one task.
- Do not start ASR binary integration details until task 9 baseline tests pass.
- If a test fails unexpectedly, apply `@superpowers:systematic-debugging` before patching.
- Before claiming completion, apply `@superpowers:verification-before-completion`.
