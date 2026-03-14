# Code Quality Issues

Analysis of concrete bugs, risks, and architectural issues found in the codebase.

**Last Updated**: 2026-03-14
**Status**: All P0 and P1 bugs have been fixed ✅

---

## ✅ Fixed: P0 Bugs (Runtime Errors)

### 1. `ASRSummary` Parameter Name Error
**Location:** `src/application/asr_coordinator.py:165`

`ASRSummary(total=...)` used wrong keyword argument, but dataclass field is `total_files`. Would throw `TypeError: unexpected keyword argument 'total'` when ASR completes.

**Fix Applied:** Changed `total=` to `total_files=`

---

### 2. GPU Fallback Status Reporting Error
**Location:** `src/asr/whisper_transcriber.py:68-77`

When GPU init fails and falls back to CPU, `runtime_use_gpu` remains True because it's set before the fallback logic runs. Users see incorrect GPU status.

**Fix Applied:** Use local variable `use_gpu` to track actual backend used, update `runtime_use_gpu` correctly after fallback.

---

### 3. Filename Substring Matching Error
**Location:** `src/gui/app.py:1482`

Auto-cleanup uses `if basename in message` substring matching, causing false positives (e.g., "test.srt" matches "contest.srt").

**Fix Applied:** Extract full output path from message format, use exact basename comparison.

---

### 4. O(n²) Deduplication Logic
**Location:** `src/gui/app.py:1190-1210`

When adding files to list, code loops through entire listbox for each file to check duplicates. Performance degrades significantly with large file counts.

**Fix Applied:** Build a set of existing paths before loop for O(1) lookup.

---

### 5. ASR Coordinator - Incorrect Success Tracking
**Location:** `src/application/asr_coordinator.py:149`

`successful += 1` is placed before `break` inside try block. If an exception occurs after incrementing but before break, the file could be counted as both successful and failed.

**Fix Applied:** Moved `successful += 1` after all operations complete, before `break`.

---

### 6. Translation Coordinator - Subtitle Loss on Partial Failure
**Location:** `src/application/translation_coordinator.py:95-135`

When a subtitle translation fails, `file_failed` is set to True but the file is still saved with partial translations. This creates corrupted output files with mixed translated/untranslated content.

**Fix Applied:** Stop processing remaining subtitles when one fails, and only save the file if all subtitles were successfully translated.

---

## ✅ Fixed: P1 Bugs (High Priority)

### 7. Thread Safety Issue with `queue_items`
**Location:** `src/gui/app.py`

`queue_items` list is accessed from both main thread (GUI) and background threads without synchronization, risking race conditions and data corruption.

**Fix Applied:** Added `queue_items_lock` (threading.Lock) and protected all access points with lock.

---

### 8. GUI - Blocking thread.join()
**Location:** `src/gui/app.py:1033`

Legacy `TranslationThread` uses `thread.join()` which blocks the UI thread until translation completes, freezing the entire application.

**Fix Applied:** Removed `thread.join()` call. The thread already has callback mechanism via `file_translated()`.

---

### 9. GUI - Nonsensical cget() Call
**Location:** `src/gui/app.py:1062`

Code calls `self.audio_path_label.cget("from")` which retrieves a non-existent "from" config option and discards the result. This serves no purpose.

**Fix Applied:** Removed the nonsensical line.

---

### 10. Ollama Client - Unused Status Code Retrieval
**Location:** `src/infrastructure/translation/ollama_translation_client.py`

Code retrieved HTTP status code but never used it for any logic or error handling.

**Fix Applied:** Removed unused status code retrieval, simplified logging.

---

## ✅ Fixed: P2 Bugs (Medium Priority)

### 11. Translation Coordinator - Missing Exception Logging
**Location:** `src/application/translation_coordinator.py:130`

Inner exception handler uses bare `except Exception:` without capturing the exception object, making debugging difficult.

**Fix Applied:** Changed to `except Exception as exc:` and added `exc` to log message.

---

### 12. Whisper Transcriber - Missing Error Handling for Audio Conversion
**Location:** `src/asr/whisper_transcriber.py:110-111`

Audio conversion can fail (corrupt file, unsupported format, missing codecs) but there's no try-except around it. Errors propagate as generic exceptions.

**Fix Applied:** Added try-except block with clear error message indicating audio conversion failure.

---

### 13. Missing Module-Level Logger Definitions
**Location:** `src/asr/whisper_transcriber.py` and `src/asr/whisper_wrapper.py`

The `save_output` function and version check functions use `logger` but it was never defined at module level, causing `NameError: name 'logger' is not defined` at runtime.

**Fix Applied:** Added `logger = get_logger(__name__)` to both files.

---

## ✅ New Feature Added

### 14. Auto-install/upgrade yt-dlp at Startup
**Location:** `src/main.py`

Added `ensure_yt_dlp()` function that runs at application startup to automatically check and upgrade yt-dlp, ensuring users always have the latest version for YouTube downloads.

---

## ✅ Prompt Optimization

### 15. Rewrote Default Translation Prompt
**Location:** `src/translation/prompts.json`

Reduced prompt from ~1800 characters to ~170 characters (90% reduction) by:
- Removing verbose English instructions
- Removing redundant examples
- Keeping only essential rules
- Using more concise Chinese phrasing

**Impact:** Significant token savings on every translation request, reducing API costs and latency.

---

## ✅ Debug Logging Enhancements

Added comprehensive debug logging to:
- **GUI app.py**: Queue operations, file selection, URL parsing, file cleanup, queue processing
- **ASR coordinator**: Model initialization, transcription progress, GPU backend status, output saving
- **Ollama translation client**: HTTP requests/responses, error categorization (HTTPError, URLError, JSONDecodeError)
- **File operations**: Added/skipped file tracking, duplicate detection
- **Whisper transcriber**: Audio conversion errors

All logging follows best practices:
- DEBUG: Detailed execution flow and state changes
- INFO: Key milestones and successful operations
- WARNING: Recoverable issues and unexpected states
- ERROR: Failures with context

---

## P2 Level - Architectural Improvements (Not Yet Addressed)

### 16. Hardcoded Ollama Endpoint
**Location:** `src/main.py:26`
**Issue:** Ollama URL is hardcoded, cannot be configured
**Suggestion:** Add config file or environment variable support

### 17. Missing Input Validation
**Location:** Multiple places
**Issue:** User inputs not sufficiently validated (file paths, URLs, language codes, etc.)
**Suggestion:** Add unified input validation layer

### 18. Inconsistent Error Handling
**Location:** Multiple places
**Issue:** Some places use exceptions, others return None
**Suggestion:** Unify error handling strategy

### 19. Improper Log Level Usage
**Location:** Multiple places
**Issue:** Some warnings should be errors, some info should be debug
**Suggestion:** Review and standardize log level usage

---

**Summary**: All critical bugs (P0, P1, P2) have been fixed. The application now runs without runtime errors, with correct GPU fallback reporting, accurate file cleanup, better performance, thread-safe operations, non-blocking UI, proper error handling, comprehensive debug logging, and optimized prompts. All 24 unit tests pass ✅
