# Code Review Issues

**Date:** 2026-03-11
**Reviewed by:** Codex (gpt-5.2-codex)
**Project:** ai-whisper-translator

---

## Summary

This document contains findings from a comprehensive code review of the ai-whisper-translator project, focusing on the new ASR integration (whisper.cpp), GUI implementation, dependencies, and overall maintainability.

**Total Issues:**
- 🔴 Critical: 5
- ⚠️ Important: 5
- 📝 Minor/Quality: 6
- 🏗️ Architecture: 3

---

## 🔴 Critical Issues (Priority: High)

### 1. Auto Language Detection is Effectively Disabled

**Files Affected:**
- `src/gui/app.py`
- `src/application/asr_coordinator.py`
- `src/asr/whisper_wrapper.py`

**Issue:**
- GUI maps "Auto Detect" to `None`
- `ASRCoordinator` passes `None` through
- `WhisperWrapper.get_full_params()` only enables detection if `language == "auto"`
- **Result:** "Auto Detect" UI option does not detect language at all

**Recommendation:**
```python
# In ASRCoordinator or WhisperWrapper
if language is None or language == "auto":
    params.detect_language = True
```

---

### 2. ASR Coordinator Doesn't Close Whisper Contexts (Memory Leak Risk)

**Files Affected:**
- `src/application/asr_coordinator.py`
- `src/asr/whisper_transcriber.py`

**Issue:**
- `ASRCoordinator.run()` creates a `Transcriber` but never calls `close()`
- Multiple runs can cause context accumulation
- Each context holds GPU memory and model data

**Recommendation:**
```python
# Option 1: Use context manager
def run(self, request: ASRRequest):
    with Transcriber(...) as transcriber:
        result = transcriber.transcribe_file(...)
        return result

# Option 2: Use finally block
def run(self, request: ASRRequest):
    transcriber = Transcriber(...)
    try:
        result = transcriber.transcribe_file(...)
        return result
    finally:
        transcriber.close()
```

---

### 3. GUI Blocks on YouTube Downloads

**Files Affected:**
- `src/gui/app.py`

**Issue:**
- `download_from_youtube()` runs synchronously on UI thread
- `yt-dlp` calls will freeze the entire GUI
- No progress updates during download

**Recommendation:**
```python
import threading
from queue import Queue

def download_from_youtube(self):
    def download_thread():
        try:
            path = self.downloader.download(url)
            self.after(0, lambda: self._on_download_complete(path))
        except Exception as e:
            self.after(0, lambda: self._on_download_error(e))

    thread = threading.Thread(target=download_thread)
    thread.daemon = True
    thread.start()
```

---

### 4. Whisper.cpp ABI Mismatch Risk

**Files Affected:**
- `src/asr/whisper_wrapper.py`

**Issue:**
- ctypes struct definitions are long and tightly coupled to whisper.cpp headers
- If local whisper.cpp version differs, it can crash or misbehave at runtime
- No version checking or compatibility guards

**Recommendation:**
```python
# Option 1: Pin whisper.cpp version
WHISPER_CPP_VERSION = "1.8.3"
WHISPER_CPP_COMMIT = "abc123def"

# Option 2: Generate ctypes from headers
# Use tools like ctypesgen or manual code generation

# Option 3: Add version guard
def check_whisper_version():
    actual_version = wrapper.lib.whisper_version_major()
    if actual_version != EXPECTED_VERSION:
        raise RuntimeError(f"Whisper.cpp version mismatch: {actual_version} != {EXPECTED_VERSION}")
```

---

### 5. whisper.cpp Directory Untracked but Not Ignored

**Files Affected:**
- `.gitignore`
- `whisper.cpp/`

**Issue:**
- Repo has untracked `whisper.cpp/` directory
- `.gitignore` has it commented out
- No git submodule configured
- Risks:
  - Keeps showing up as untracked
  - Accidental commits of huge dependency (226.1 MB)
  - Unclear installation instructions for new developers

**Recommendation:**
```bash
# Option 1: Use git submodule
git submodule add https://github.com/ggerganov/whisper.cpp.git whisper.cpp
echo "whisper.cpp/" >> .gitignore

# Option 2: Re-enable ignore with install docs
# Uncomment in .gitignore:
# whisper.cpp/

# Add to README:
# Installing whisper.cpp
# git clone https://github.com/ggerganov/whisper.git whisper.cpp
# cd whisper.cpp && make
```

---

## ⚠️ Important Issues (Priority: Medium)

### 1. UI Language Switch Does Not Update ASR Tab

**Files Affected:**
- `src/gui/app.py`

**Issue:**
- `update_ui_language()` only updates translate-tab controls
- ASR labels and dropdowns stay in old language
- Some labels are hardcoded in Chinese

**Recommendation:**
```python
def update_ui_language(self, lang_code):
    # Update existing translate tab
    self._update_translate_tab_lang(lang_code)

    # Add ASR tab updates
    self._update_asr_tab_lang(lang_code)

def _update_asr_tab_lang(self, lang_code):
    translations = {
        'zh-TW': {'asr_tab': '音訊轉錄', ...},
        'en': {'asr_tab': 'Audio Transcription', ...}
    }
    # Apply translations to ASR controls
```

---

### 2. `gpu_backend` is Collected But Unused

**Files Affected:**
- `src/application/asr_coordinator.py`
- `src/asr/whisper_transcriber.py`
- `src/asr/whisper_wrapper.py`

**Issue:**
- `ASRRequest.gpu_backend` is passed through `ASRCoordinator` and stored in `Transcriber`
- Never affects whisper.cpp parameters
- Misleading UI (user thinks backend selection works)

**Recommendation:**
```python
# Option 1: Implement backend selection
def get_full_params(self, gpu_backend: str):
    params = self.lib.whisper_full_default_params(WhisperSamplingStrategy.WHISPER_SAMPLING_GREEDY)
    if gpu_backend == "metal":
        params.use_gpu = True
        params.gpu_device = 0  # Metal
    # ... other backends
    return params

# Option 2: Remove setting
# Remove gpu_backend from ASRRequest and UI
```

---

### 3. Temporary Files from ffmpeg Conversions Are Never Cleaned

**Files Affected:**
- `src/asr/audio_converter.py`

**Issue:**
- When `_convert_with_ffmpeg()` writes a temp file, it doesn't delete it after reading
- Can accumulate temp files in system temp directory
- Wastes disk space

**Recommendation:**
```python
def _convert_with_ffmpeg(self, input_path: str, output_path: str) -> str:
    temp_file = None
    try:
        if not output_path:
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            output_path = temp_file.name
        # ... conversion logic ...
        return output_path
    finally:
        if temp_file and os.path.exists(temp_file.name):
            os.unlink(temp_file.name)
```

---

### 4. YouTube Output Filename Sanitization Mismatch

**Files Affected:**
- `src/asr/audio_downloader.py`

**Issue:**
- You compute `safe_title` for searching but don't tell yt-dlp to restrict filenames
- On Windows/macOS, invalid characters can still produce errors
- Race condition between sanitization and yt-dlp's own naming

**Recommendation:**
```python
ydl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'wav',
        'preferredquality': '192',
    }],
    'restrictfilenames': True,  # Add this
    'outtmpl': str(self.output_dir / '%(title)s.%(ext)s'),
}
```

---

### 5. `.gitignore` Now Ignores `test_*.py`

**Files Affected:**
- `.gitignore`

**Issue:**
- Will ignore new tests (including ones at repo root)
- `test_gui.py`, `test_imports.py`, etc. at root will be ignored
- Can hide important test files

**Recommendation:**
```gitignore
# Remove this line:
# test_*.py

# Instead, ignore specific test artifacts if needed:
# **/test_outputs/
# **/.pytest_cache/
```

---

## 📝 Minor / Quality Notes

### 1. `get_logger()` Global State Issue

**File:** `src/asr/utils/logger.py`

**Issue:**
- Uses a global `_logger` but returns `logging.getLogger(name)` every time
- Global cache doesn't help because it's not used

**Recommendation:**
```python
_logger = None

def get_logger(name: str = "asr") -> logging.Logger:
    global _logger
    if _logger is None:
        _logger = logging.getLogger(name)
    return _logger  # Return the cached logger
```

---

### 2. Unused `check_dependencies()` Function

**File:** `src/asr/audio_converter.py`

**Issue:**
- `AudioConverter.check_dependencies()` is defined but never called
- Could warn users early about missing ffmpeg or libsndfile

**Recommendation:**
```python
# In app initialization
if not AudioConverter.check_dependencies():
    messagebox.showwarning("Dependencies Missing",
                        "ffmpeg or libsndfile is not installed.")
```

---

### 3. Inefficient Audio Sample Copying

**File:** `src/asr/whisper_transcriber.py`

**Issue:**
- Uses `ctypes.c_float * len(audio_samples)` which copies data
- For large audio files, this is slow and memory-heavy

**Recommendation:**
```python
# Instead of copying:
samples_ptr = (ctypes.c_float * len(audio_samples))(*audio_samples)

# Use numpy pointer:
samples_array = np.ascontiguousarray(audio_samples, dtype=np.float32)
samples_ptr = samples_array.ctypes.data_as(ctypes.POINTER(ctypes.c_float))
```

---

### 4. Potential Typo in `select_audio()`

**File:** `src/gui/app.py`

**Issue:**
- `self.audio_path_label.cget("from")` - "from" is not a valid option for Label
- Likely meant to get another attribute

**Recommendation:**
```python
# Verify what you're trying to get
# Probably one of these:
# self.audio_path_label.cget("text")
# self.audio_path_label.cget("font")
```

---

## 🏗️ Architecture / Maintainability Observations

### 1. GUI is Too Large (Monolithic)

**File:** `src/gui/app.py` (440+ lines)

**Issue:**
- Handles translation + ASR + language switching + dialogs + menu logic in one class
- Difficult to test individual components
- Hard to maintain and evolve

**Recommendation:**
```
src/gui/
├── __init__.py
├── app.py                    # Main orchestration only
├── translate_tab.py          # Translation UI
├── asr_tab.py              # ASR UI
├── dialogs.py              # Message dialogs
├── language_manager.py     # Localization
└── widgets.py             # Custom widgets
```

---

### 2. ASR Coordinator Design Inconsistency

**File:** `src/application/asr_coordinator.py`

**Issue:**
- Only supports single-file transcription
- `ASRRequest` and summary types suggest future batching
- Not used yet

**Recommendation:**
```python
# Either implement batching:
@dataclass
class ASRRequest:
    input_paths: List[str]  # Multiple files
    output_path: str

# Or simplify to single-file:
@dataclass
class ASRRequest:
    input_path: str  # Single file
    output_path: str
```

---

### 3. Inconsistent Error Handling

**Files:** Multiple GUI files

**Issue:**
- No consistent error surface for ASR errors
- Some show `messagebox`, some update status label
- User gets different experiences

**Recommendation:**
```python
class ASRError(Exception):
    pass

def _handle_asr_error(self, error: Exception):
    logger.error(f"ASR error: {error}", exc_info=True)
    messagebox.showerror("ASR Error", str(error))
    self.update_status(f"Error: {error}")
```

---

## 📦 Dependencies Review (pyproject.toml)

### Issues:

1. **`tkinterdnd2` is included but disabled in code**
   - Declared as dependency but drag/drop is commented out
   - Should be optional or removed

2. **System dependencies not documented**
   - `ffmpeg` - required for audio conversion and YouTube download
   - `libsndfile` - required by `soundfile` package
   - `tk` - Python GUI library

3. **No explicit whisper.cpp dependency**
   - External C library, no clear installation path

### Recommendations:

```toml
[project]
dependencies = [
  "pysrt>=1.1.2",
  # "tkinterdnd2>=0.3.0",  # Remove or move to optional
  "yt-dlp>=2023.11.16",
  "numpy>=1.24.0",
  "soundfile>=0.12.1",
]

[project.optional-dependencies]
gui-dragdrop = ["tkinterdnd2>=0.3.0"]
```

```markdown
## System Dependencies

### Required
- Python 3.10+
- tk (Python GUI library)
- ffmpeg (audio conversion, YouTube download)
- libsndfile (soundfile dependency)

### Installing on macOS
```bash
brew install ffmpeg libsndfile
```

### Installing on Ubuntu/Debian
```bash
sudo apt-get install ffmpeg libsndfile1
```

### whisper.cpp
See [INSTALL_WHISPER.md](INSTALL_WHISPER.md) for detailed instructions.
```

---

## 🎯 Suggested Fix Order (Shortlist)

1. Fix auto language detection flow (`None` vs `"auto"`)
2. Ensure `Transcriber` context is always freed
3. Make YouTube download non-blocking in GUI
4. Add ASR UI localization updates
5. Clarify whisper.cpp dependency management (submodule or ignore + install docs)
6. Remove `test_*.py` ignore from `.gitignore`

---

## 📊 Summary Statistics

| Category | Count |
|----------|-------|
| Critical Issues | 5 |
| Important Issues | 5 |
| Minor/Quality Issues | 4 |
| Architecture Issues | 3 |
| Dependency Issues | 3 |
| **Total** | **20** |

---

## 📝 Notes

- Tests were not run (not requested)
- Review focused on staged changes and untracked files
- All findings based on static code analysis
- No security audit was performed

---

**Next Steps:**

1. Decide on whisper.cpp management approach
2. Fix critical issues (memory leak, auto-detect, blocking UI)
3. Refactor GUI into smaller modules for maintainability
4. Add integration tests for ASR workflow
5. Document system dependencies clearly

