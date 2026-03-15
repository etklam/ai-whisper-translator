# PyInstaller No-Model Release Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Produce separate Windows `.exe` and macOS `.app` PyInstaller releases that bundle the platform ASR runtimes but exclude Whisper models, while adding an in-app guided model download flow for `ggml-*.bin` files.

**Architecture:** Keep release work split by platform: Windows bundles `Const-me/Whisper` runtime assets, macOS bundles `whisper.cpp + Metal`. The GUI owns first-run model onboarding through a small download service and status-driven prompts, while packaging scripts and PyInstaller specs bundle only application code plus native runtime libraries, never models.

**Tech Stack:** Python 3.10+, Tkinter, PyInstaller, pytest, PowerShell, shell scripts, urllib/request downloads, platform-native runtime assets

---

### Task 1: Add failing tests for release settings and model-onboarding defaults

**Files:**
- Modify: `tests/unit/application/test_models.py`
- Modify: `src/application/settings_models.py`
- Modify: `src/gui/config/settings_store.py`

**Step 1: Write the failing test**

```python
def test_default_settings_keep_model_path_empty_for_release_onboarding():
    settings = AppSettings()
    assert settings.asr_model_path == ""
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_models.py::test_default_settings_keep_model_path_empty_for_release_onboarding -v -p no:cacheprovider`
Expected: FAIL because the current defaults still assume an existing bundled model path.

**Step 3: Write minimal implementation**

Change the default settings path assumptions so release builds can start with no model configured and rely on in-app onboarding instead of bundled models.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_models.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_models.py src/application/settings_models.py src/gui/config/settings_store.py
git commit -m "feat: default release settings to no bundled model"
```

### Task 2: Add failing tests for a shared model catalog and download URL resolver

**Files:**
- Create: `tests/unit/application/test_model_catalog.py`
- Create: `src/application/model_catalog.py`

**Step 1: Write the failing test**

```python
def test_model_catalog_returns_huggingface_ggml_download_url():
    url = build_model_download_url("base")
    assert url.endswith("ggml-base.bin?download=true")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_model_catalog.py::test_model_catalog_returns_huggingface_ggml_download_url -v -p no:cacheprovider`
Expected: FAIL because there is no shared model catalog helper yet.

**Step 3: Write minimal implementation**

Add a shared model catalog module with:
- supported model keys
- default model key
- download URL builder
- default release model directory per platform

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_model_catalog.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_model_catalog.py src/application/model_catalog.py
git commit -m "feat: add shared whisper model catalog"
```

### Task 3: Add failing tests for model download service behavior

**Files:**
- Create: `tests/unit/application/test_model_download_service.py`
- Create: `src/application/model_download_service.py`

**Step 1: Write the failing test**

```python
def test_model_download_service_streams_to_target_path(tmp_path):
    target = tmp_path / "ggml-base.bin"
    service = ModelDownloadService(fetcher=fake_fetcher)
    service.download_model("base", target)
    assert target.read_bytes() == b"chunk-achunk-b"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_model_download_service.py::test_model_download_service_streams_to_target_path -v -p no:cacheprovider`
Expected: FAIL because the download service does not exist.

**Step 3: Write minimal implementation**

Add a small application-level download service that:
- validates the selected model key
- creates parent directories
- downloads to a temporary file first
- renames atomically into place

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_model_download_service.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_model_download_service.py src/application/model_download_service.py
git commit -m "feat: add model download service"
```

### Task 4: Add failing tests for model download progress events

**Files:**
- Modify: `tests/unit/application/test_models.py`
- Modify: `src/application/events.py`

**Step 1: Write the failing test**

```python
def test_model_download_progress_event_fields():
    event = ModelDownloadProgressEvent(model_key="base", downloaded_bytes=10, total_bytes=100)
    assert event.model_key == "base"
    assert event.total_bytes == 100
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_models.py::test_model_download_progress_event_fields -v -p no:cacheprovider`
Expected: FAIL because there is no dedicated event model for model download progress.

**Step 3: Write minimal implementation**

Add typed application events for:
- download started
- download progress
- download completed
- download failed

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_models.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_models.py src/application/events.py
git commit -m "feat: add model download event types"
```

### Task 5: Add failing tests for GUI first-run model onboarding state

**Files:**
- Create: `tests/unit/presentation/test_model_onboarding.py`
- Modify: `src/gui/app.py`
- Modify: `src/gui/resources/translations.py`
- Modify: `src/gui/views/asr_panel.py`

**Step 1: Write the failing test**

```python
def test_missing_model_state_shows_download_cta():
    state = build_model_onboarding_state(model_path="", file_exists=False)
    assert state["needs_download"] is True
    assert state["cta"] == "download"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/presentation/test_model_onboarding.py::test_missing_model_state_shows_download_cta -v -p no:cacheprovider`
Expected: FAIL because the GUI has no explicit onboarding state helper.

**Step 3: Write minimal implementation**

Add a small GUI-facing helper and wiring so the ASR panel can distinguish:
- no model configured
- model path configured but file missing
- model ready

Do not add the full download flow yet; only state and CTA rendering.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/presentation/test_model_onboarding.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_model_onboarding.py src/gui/app.py src/gui/resources/translations.py src/gui/views/asr_panel.py
git commit -m "feat: add gui model onboarding state"
```

### Task 6: Add failing tests for the GUI-triggered model download workflow

**Files:**
- Modify: `tests/unit/presentation/test_model_onboarding.py`
- Modify: `src/gui/app.py`
- Modify: `src/gui/presenters/queue_execution.py`

**Step 1: Write the failing test**

```python
def test_download_model_action_updates_model_path_after_success(monkeypatch):
    app = FakeApp()
    run_model_download(app, model_key="base")
    assert app.asr_model_path_value.endswith("ggml-base.bin")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/presentation/test_model_onboarding.py::test_download_model_action_updates_model_path_after_success -v -p no:cacheprovider`
Expected: FAIL because there is no GUI model download action yet.

**Step 3: Write minimal implementation**

Add a GUI action that:
- picks the selected/default model
- starts the download service in a worker thread
- updates progress text
- writes the completed model path back into config/UI

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/presentation/test_model_onboarding.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/presentation/test_model_onboarding.py src/gui/app.py src/gui/presenters/queue_execution.py
git commit -m "feat: add gui model download workflow"
```

### Task 7: Add failing tests for blocking ASR when runtime is missing vs model is missing

**Files:**
- Modify: `tests/unit/application/test_asr_coordinator.py`
- Modify: `src/application/asr_coordinator.py`
- Modify: `src/domain/errors.py`

**Step 1: Write the failing test**

```python
def test_asr_coordinator_raises_model_guidance_error_when_model_missing(tmp_path):
    request = ASRRequest(input_path=str(input_path), output_path=str(output_path), model_path=str(tmp_path / "missing.bin"))
    with pytest.raises(ModelNotReadyError):
        coordinator.run(request)
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/application/test_asr_coordinator.py::test_asr_coordinator_raises_model_guidance_error_when_model_missing -v -p no:cacheprovider`
Expected: FAIL because missing model and missing runtime are not distinguished cleanly.

**Step 3: Write minimal implementation**

Split the coordinator error path so the GUI can show a model download prompt for model-missing cases without pretending the ASR runtime itself is broken.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/application/test_asr_coordinator.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/application/test_asr_coordinator.py src/application/asr_coordinator.py src/domain/errors.py
git commit -m "feat: separate model-missing and runtime-missing asr errors"
```

### Task 8: Add failing tests for Windows runtime manifest and bundle layout

**Files:**
- Create: `tests/unit/infrastructure/runtime/test_release_manifest.py`
- Create: `src/infrastructure/runtime/release_manifest.py`

**Step 1: Write the failing test**

```python
def test_windows_release_manifest_targets_const_me_runtime():
    manifest = build_release_manifest(platform_name="win32")
    assert manifest.asr_provider == "const_me"
    assert "runtime/asr/const-me" in manifest.runtime_dirs
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/infrastructure/runtime/test_release_manifest.py::test_windows_release_manifest_targets_const_me_runtime -v -p no:cacheprovider`
Expected: FAIL because there is no release manifest describing bundled runtime assets.

**Step 3: Write minimal implementation**

Create a release manifest that maps:
- platform -> provider
- runtime directories to bundle
- default model directory outside the bundled app

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/runtime/test_release_manifest.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/infrastructure/runtime/test_release_manifest.py src/infrastructure/runtime/release_manifest.py
git commit -m "feat: add release runtime manifest"
```

### Task 9: Add failing tests for Windows runtime collection script

**Files:**
- Create: `tests/unit/packaging/test_windows_release_packaging.py`
- Create: `packaging/windows/prepare-release-runtime.ps1`
- Modify: `packaging/windows/setup-whisper-cpp.ps1`

**Step 1: Write the failing test**

```python
def test_windows_release_runtime_script_mentions_const_me_output_directory():
    script = Path("packaging/windows/prepare-release-runtime.ps1").read_text(encoding="utf-8")
    assert "runtime/asr/const-me" in script
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_windows_release_packaging.py::test_windows_release_runtime_script_mentions_const_me_output_directory -v -p no:cacheprovider`
Expected: FAIL because the Windows release runtime prep script does not exist.

**Step 3: Write minimal implementation**

Create a Windows release-prep script that stages `Const-me/Whisper` runtime binaries into a deterministic bundle directory without downloading any models.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_windows_release_packaging.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_windows_release_packaging.py packaging/windows/prepare-release-runtime.ps1 packaging/windows/setup-whisper-cpp.ps1
git commit -m "feat: add windows release runtime staging script"
```

### Task 10: Add failing tests for macOS runtime collection script

**Files:**
- Create: `tests/unit/packaging/test_macos_release_packaging.py`
- Create: `packaging/macos/prepare-release-runtime.sh`
- Modify: `packaging/macos/setup-whisper-cpp.sh`

**Step 1: Write the failing test**

```python
def test_macos_release_runtime_script_mentions_whisper_cpp_runtime_directory():
    script = Path("packaging/macos/prepare-release-runtime.sh").read_text(encoding="utf-8")
    assert "runtime/asr/whisper.cpp" in script
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_macos_release_packaging.py::test_macos_release_runtime_script_mentions_whisper_cpp_runtime_directory -v -p no:cacheprovider`
Expected: FAIL because the macOS release runtime prep script does not exist.

**Step 3: Write minimal implementation**

Create a macOS release-prep script that stages `whisper.cpp + Metal` dynamic libraries into a deterministic bundle directory without downloading any models.

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_macos_release_packaging.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_macos_release_packaging.py packaging/macos/prepare-release-runtime.sh packaging/macos/setup-whisper-cpp.sh
git commit -m "feat: add macos release runtime staging script"
```

### Task 11: Add failing tests for Windows PyInstaller spec wiring

**Files:**
- Modify: `tests/unit/packaging/test_windows_release_packaging.py`
- Modify: `packaging/windows/pyinstaller.spec`

**Step 1: Write the failing test**

```python
def test_windows_pyinstaller_spec_builds_exe_without_models():
    content = Path("packaging/windows/pyinstaller.spec").read_text(encoding="utf-8")
    assert "runtime/asr/const-me" in content
    assert "ggml-" not in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_windows_release_packaging.py::test_windows_pyinstaller_spec_builds_exe_without_models -v -p no:cacheprovider`
Expected: FAIL because the spec file is still a placeholder.

**Step 3: Write minimal implementation**

Implement the Windows spec so it:
- bundles app code
- includes staged `Const-me` runtime assets
- excludes model files
- outputs a GUI executable profile

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_windows_release_packaging.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_windows_release_packaging.py packaging/windows/pyinstaller.spec
git commit -m "feat: wire windows pyinstaller release spec"
```

### Task 12: Add failing tests for macOS PyInstaller spec wiring

**Files:**
- Modify: `tests/unit/packaging/test_macos_release_packaging.py`
- Modify: `packaging/macos/pyinstaller.spec`

**Step 1: Write the failing test**

```python
def test_macos_pyinstaller_spec_builds_app_without_models():
    content = Path("packaging/macos/pyinstaller.spec").read_text(encoding="utf-8")
    assert "runtime/asr/whisper.cpp" in content
    assert "BUNDLE(" in content
    assert "ggml-" not in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_macos_release_packaging.py::test_macos_pyinstaller_spec_builds_app_without_models -v -p no:cacheprovider`
Expected: FAIL because the spec file is still a placeholder.

**Step 3: Write minimal implementation**

Implement the macOS spec so it:
- builds a `.app`
- bundles staged `whisper.cpp + Metal` runtime assets
- excludes model files
- includes the correct windowed app configuration

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_macos_release_packaging.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_macos_release_packaging.py packaging/macos/pyinstaller.spec
git commit -m "feat: wire macos pyinstaller release spec"
```

### Task 13: Add failing tests for release build entry scripts

**Files:**
- Create: `tests/unit/packaging/test_release_commands.py`
- Create: `packaging/windows/build-release.ps1`
- Create: `packaging/macos/build-release.sh`
- Modify: `docs/packaging.md`

**Step 1: Write the failing test**

```python
def test_windows_build_release_script_invokes_pyinstaller_spec():
    script = Path("packaging/windows/build-release.ps1").read_text(encoding="utf-8")
    assert "pyinstaller" in script.lower()
    assert "packaging/windows/pyinstaller.spec" in script
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_release_commands.py::test_windows_build_release_script_invokes_pyinstaller_spec -v -p no:cacheprovider`
Expected: FAIL because there is no release build entry script yet.

**Step 3: Write minimal implementation**

Create one release command per platform that:
- prepares runtime assets
- runs PyInstaller
- writes output into a predictable `dist-release/` folder
- does not fetch or package models

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_release_commands.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_release_commands.py packaging/windows/build-release.ps1 packaging/macos/build-release.sh docs/packaging.md
git commit -m "feat: add platform release build entry scripts"
```

### Task 14: Add failing tests for release-facing GUI copy and docs

**Files:**
- Modify: `tests/unit/packaging/test_update_asr_config.py`
- Modify: `README.md`
- Modify: `README_ZH.md`
- Modify: `docs/TECHNICAL.md`
- Modify: `docs/TECHNICAL_ZH.md`
- Modify: `docs/packaging.md`
- Modify: `src/gui/resources/translations.py`

**Step 1: Write the failing test**

```python
def test_packaging_docs_describe_no_model_pyinstaller_release():
    content = Path("docs/packaging.md").read_text(encoding="utf-8")
    assert "does not bundle Whisper models" in content
    assert "download model" in content
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_update_asr_config.py -k packaging_docs_describe_no_model_pyinstaller_release -v -p no:cacheprovider`
Expected: FAIL because the docs do not yet describe the final release posture.

**Step 3: Write minimal implementation**

Document:
- Windows `.exe` release
- macOS `.app` release
- bundled runtimes only
- no bundled models
- in-app model download onboarding
- exact release commands

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/packaging/test_release_commands.py -v -p no:cacheprovider`
Run: `pytest tests/unit/presentation/test_model_onboarding.py -v -p no:cacheprovider`
Run: `pytest tests/unit/packaging/test_update_asr_config.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/unit/packaging/test_update_asr_config.py README.md README_ZH.md docs/TECHNICAL.md docs/TECHNICAL_ZH.md docs/packaging.md src/gui/resources/translations.py
git commit -m "docs: describe no-model pyinstaller release flow"
```

### Task 15: Verify end-to-end release readiness

**Files:**
- Modify: `packaging/windows/build-release.ps1`
- Modify: `packaging/macos/build-release.sh`

**Step 1: Write the failing verification checklist test**

```python
def test_release_scripts_emit_dist_release_targets():
    ...
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/unit/packaging/test_release_commands.py -k dist_release -v -p no:cacheprovider`
Expected: FAIL until the release scripts consistently emit the final artifact locations.

**Step 3: Write minimal implementation**

Finish the scripts and checklist so release verification can confirm:
- Windows artifact path
- macOS artifact path
- no bundled `ggml-*.bin`
- runtime directories present

**Step 4: Run test to verify it passes**

Run: `pytest tests/unit/infrastructure/asr/test_provider_selection.py -v -p no:cacheprovider`
Run: `pytest tests/unit/application/test_models.py tests/unit/application/test_model_catalog.py tests/unit/application/test_model_download_service.py tests/unit/application/test_asr_coordinator.py -v -p no:cacheprovider`
Run: `pytest tests/unit/presentation/test_settings_store.py tests/unit/presentation/test_model_onboarding.py -v -p no:cacheprovider`
Run: `pytest tests/unit/packaging/test_update_asr_config.py tests/unit/packaging/test_windows_release_packaging.py tests/unit/packaging/test_macos_release_packaging.py tests/unit/packaging/test_release_commands.py -v -p no:cacheprovider`
Expected: PASS

**Step 5: Commit**

```bash
git add packaging/windows/build-release.ps1 packaging/macos/build-release.sh packaging/windows/pyinstaller.spec packaging/macos/pyinstaller.spec packaging/windows/prepare-release-runtime.ps1 packaging/macos/prepare-release-runtime.sh docs/packaging.md tests/unit/application/test_model_catalog.py tests/unit/application/test_model_download_service.py tests/unit/presentation/test_model_onboarding.py tests/unit/packaging/test_windows_release_packaging.py tests/unit/packaging/test_macos_release_packaging.py tests/unit/packaging/test_release_commands.py
git commit -m "feat: add no-model pyinstaller release workflow"
```
