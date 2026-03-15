# Windows Const-me / macOS Whisper.cpp Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Switch Windows ASR runtime to `Const-me/Whisper` while preserving `whisper.cpp + Metal` on macOS behind a provider-based abstraction.

**Architecture:** Introduce a provider split at the infrastructure boundary so Windows and macOS use different native adapters but share the same application-level ASR contract. Resolve provider selection from config and platform, validate unsupported combinations early, and keep UI/workflow code provider-agnostic.

**Tech Stack:** Python 3.10+, ctypes, pytest, PowerShell packaging scripts, shell packaging scripts, existing Tkinter application flow

---

### Task 1: Add failing tests for provider resolution defaults

**Files:**
- Create: `tests/unit/infrastructure/asr/test_provider_selection.py`
- Modify: `src/infrastructure/asr/providers.py`
- Modify: `src/infrastructure/asr/backend_resolver.py`

**Step 1: Write the failing test**

```python
def test_auto_provider_resolves_to_const_me_on_windows():
    assert resolve_asr_provider("auto", platform_name="win32") == "const_me"


def test_auto_provider_resolves_to_whisper_cpp_on_macos():
    assert resolve_asr_provider("auto", platform_name="darwin") == "whisper_cpp"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py::test_auto_provider_resolves_to_const_me_on_windows -v -p no:cacheprovider`
Expected: FAIL because provider resolution helper does not exist.

**Step 3: Write minimal implementation**

Add a pure provider resolution helper and keep the mapping limited to the supported platform defaults.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/infrastructure/asr/test_provider_selection.py src/infrastructure/asr/providers.py src/infrastructure/asr/backend_resolver.py
git commit -m "feat: add platform-aware asr provider selection"
```

### Task 2: Add failing tests for unsupported provider validation

**Files:**
- Modify: `tests/unit/infrastructure/asr/test_provider_selection.py`
- Modify: `src/infrastructure/asr/providers.py`

**Step 1: Write the failing test**

```python
import pytest


def test_const_me_provider_is_rejected_on_macos():
    with pytest.raises(ValueError, match="const_me.*darwin"):
        resolve_asr_provider("const_me", platform_name="darwin")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py::test_const_me_provider_is_rejected_on_macos -v -p no:cacheprovider`
Expected: FAIL because unsupported combinations are not validated.

**Step 3: Write minimal implementation**

Add compatibility validation for explicit provider requests and return actionable error messages.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/infrastructure/asr/test_provider_selection.py src/infrastructure/asr/providers.py
git commit -m "feat: validate unsupported asr provider combinations"
```

### Task 3: Add failing tests for provider factory creation

**Files:**
- Modify: `tests/unit/infrastructure/asr/test_provider_selection.py`
- Modify: `src/infrastructure/asr/providers.py`
- Modify: `src/domain/services/asr_provider.py`

**Step 1: Write the failing test**

```python
def test_windows_factory_creates_const_me_provider():
    provider = create_asr_provider(
        provider_name="const_me",
        platform_name="win32",
        model_path="C:/models/ggml-base.bin",
    )
    assert provider.__class__.__name__ == "ConstMeWhisperProvider"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py::test_windows_factory_creates_const_me_provider -v -p no:cacheprovider`
Expected: FAIL because the factory does not yet build provider-specific adapters.

**Step 3: Write minimal implementation**

Add the provider factory entry points and wire them to provider-specific classes without changing application call sites yet.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/infrastructure/asr/test_provider_selection.py src/infrastructure/asr/providers.py src/domain/services/asr_provider.py
git commit -m "feat: add asr provider factory"
```

### Task 4: Add failing tests for the Windows Const-me adapter

**Files:**
- Create: `tests/unit/infrastructure/asr/test_const_me_provider.py`
- Create: `src/infrastructure/asr/const_me_provider.py`

**Step 1: Write the failing test**

```python
def test_const_me_provider_raises_clear_error_when_runtime_dll_is_missing(tmp_path):
    model_path = tmp_path / "ggml-base.bin"
    model_path.write_bytes(b"model")

    provider = ConstMeWhisperProvider(
        model_path=str(model_path),
        runtime_dir=str(tmp_path / "missing-runtime"),
    )

    with pytest.raises(FileNotFoundError, match="Const-me"):
        provider.load_model()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/asr/test_const_me_provider.py::test_const_me_provider_raises_clear_error_when_runtime_dll_is_missing -v -p no:cacheprovider`
Expected: FAIL because the adapter does not exist yet.

**Step 3: Write minimal implementation**

Create a Windows-only `ConstMeWhisperProvider` adapter with runtime path resolution, DLL loading, and normalized error handling.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_const_me_provider.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/infrastructure/asr/test_const_me_provider.py src/infrastructure/asr/const_me_provider.py
git commit -m "feat: add windows const-me whisper provider"
```

### Task 5: Add failing tests for whisper.cpp provider preservation on macOS

**Files:**
- Create: `tests/unit/infrastructure/asr/test_whisper_cpp_provider.py`
- Modify: `src/asr/whisper_transcriber.py`
- Modify: `src/infrastructure/asr/providers.py`

**Step 1: Write the failing test**

```python
def test_macos_factory_keeps_whisper_cpp_provider():
    provider = create_asr_provider(
        provider_name="whisper_cpp",
        platform_name="darwin",
        model_path="/tmp/ggml-base.bin",
    )
    assert provider.__class__.__name__ == "WhisperCppProvider"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/asr/test_whisper_cpp_provider.py::test_macos_factory_keeps_whisper_cpp_provider -v -p no:cacheprovider`
Expected: FAIL because the current whisper.cpp path is not yet exposed as a provider object.

**Step 3: Write minimal implementation**

Wrap the current whisper.cpp transcriber path in a provider adapter and keep Metal backend defaults intact on macOS.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_whisper_cpp_provider.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/infrastructure/asr/test_whisper_cpp_provider.py src/asr/whisper_transcriber.py src/infrastructure/asr/providers.py
git commit -m "feat: expose whisper.cpp runtime as macos provider"
```

### Task 6: Add failing tests for application integration

**Files:**
- Modify: `tests/unit/application/test_models.py`
- Modify: `tests/unit/application/test_translation_coordinator.py`
- Modify: `src/application/asr_coordinator.py`
- Modify: `src/application/settings_models.py`

**Step 1: Write the failing test**

```python
def test_asr_settings_include_provider_name():
    settings = ASRSettings(model_path="m.bin", asr_provider="const_me")
    assert settings.asr_provider == "const_me"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_models.py::test_asr_settings_include_provider_name -v -p no:cacheprovider`
Expected: FAIL because settings models do not yet carry provider selection.

**Step 3: Write minimal implementation**

Add `asr_provider` to the settings/application path and inject the provider factory into the coordinator without changing output behavior.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_models.py -v -p no:cacheprovider`
Run: `pytest tests/unit/application/test_translation_coordinator.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_models.py tests/unit/application/test_translation_coordinator.py src/application/asr_coordinator.py src/application/settings_models.py
git commit -m "feat: thread asr provider selection through application settings"
```

### Task 7: Add failing tests for config persistence and UI defaults

**Files:**
- Modify: `tests/unit/presentation/test_app_event_binding.py`
- Modify: `src/gui/app.py`
- Modify: `src/gui/config/settings_store.py`
- Modify: `src/gui/views/asr_panel.py`

**Step 1: Write the failing test**

```python
def test_windows_default_asr_provider_is_const_me():
    payload = build_default_settings(platform_name="win32")
    assert payload["asr_provider"] == "const_me"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/presentation/test_app_event_binding.py::test_windows_default_asr_provider_is_const_me -v -p no:cacheprovider`
Expected: FAIL because UI/config defaults do not yet expose provider selection.

**Step 3: Write minimal implementation**

Add the provider setting to persisted config and expose only the necessary UI/default wiring for platform-aware selection.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/presentation/test_app_event_binding.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_app_event_binding.py src/gui/app.py src/gui/config/settings_store.py src/gui/views/asr_panel.py
git commit -m "feat: expose asr provider selection in config and ui"
```

### Task 8: Add failing tests for Windows packaging flow

**Files:**
- Modify: `tests/unit/packaging/test_update_asr_config.py`
- Modify: `packaging/windows/setup-whisper-cpp.ps1`
- Modify: `packaging/update_asr_config.py`

**Step 1: Write the failing test**

```python
def test_windows_setup_script_mentions_const_me_runtime():
    script = Path("packaging/windows/setup-whisper-cpp.ps1").read_text(encoding="utf-8")
    assert "Const-me" in script
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_update_asr_config.py::test_windows_setup_script_mentions_const_me_runtime -v -p no:cacheprovider`
Expected: FAIL because the Windows packaging path still assumes whisper.cpp checkout/build.

**Step 3: Write minimal implementation**

Update the Windows packaging/config flow to install or resolve `Const-me/Whisper` runtime assets and write `asr_provider=const_me` into generated config.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_update_asr_config.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_update_asr_config.py packaging/windows/setup-whisper-cpp.ps1 packaging/update_asr_config.py
git commit -m "feat: switch windows asr packaging flow to const-me runtime"
```

### Task 9: Document the platform split and verify focused coverage

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `docs/TECHNICAL.md`
- Modify: `docs/TECHNICAL_ZH.md`

**Step 1: Write the failing documentation/content checks**

```python
def test_readme_mentions_windows_const_me_and_macos_whisper_cpp_split():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_update_asr_config.py -k const_me -v -p no:cacheprovider`
Expected: FAIL until docs and content checks are updated.

**Step 3: Write minimal implementation**

Document the Windows `Const-me/Whisper` runtime, the macOS `whisper.cpp + Metal` runtime, setup expectations, and unsupported platform/provider combinations.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py -v -p no:cacheprovider`
Run: `pytest tests/unit/infrastructure/asr/test_const_me_provider.py -v -p no:cacheprovider`
Run: `pytest tests/unit/infrastructure/asr/test_whisper_cpp_provider.py -v -p no:cacheprovider`
Run: `pytest tests/unit/packaging/test_update_asr_config.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add README.md README_ZH.md docs/TECHNICAL.md docs/TECHNICAL_ZH.md tests/unit/infrastructure/asr/test_provider_selection.py tests/unit/infrastructure/asr/test_const_me_provider.py tests/unit/infrastructure/asr/test_whisper_cpp_provider.py tests/unit/packaging/test_update_asr_config.py src/infrastructure/asr/providers.py src/infrastructure/asr/const_me_provider.py src/asr/whisper_transcriber.py src/application/asr_coordinator.py src/application/settings_models.py src/gui/app.py src/gui/config/settings_store.py src/gui/views/asr_panel.py packaging/windows/setup-whisper-cpp.ps1 packaging/update_asr_config.py
git commit -m "feat: split windows and macos asr runtimes by provider"
```
