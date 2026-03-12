# Single-Page ASR + Optional Translation Workflow Design

Date: 2026-03-12

## Goal
Create a single-page GUI workflow that supports batch input (YouTube URLs and local audio files), processes items sequentially, performs ASR transcription, and optionally runs translation via a checkbox (default off).

## Scope
- UI refactor to a single page with a linear workflow.
- Batch input support:
  - Multiple YouTube URLs (one per line).
  - Multiple local audio files (multi-select).
- Sequential queue processing (one item at a time).
- Optional translation step controlled by a checkbox (default unchecked).
- Translation uses legacy `TranslationThread` for now to ensure functionality.
- ASR uses existing `ASRCoordinator`.

Out of scope for this iteration:
- Refactoring translation coordinator to handle end-to-end SRT IO.
- Parallel processing.
- New automated tests.

## User Flow
1. User adds multiple YouTube URLs and/or selects multiple audio files.
2. Items appear in a unified queue list with type and source.
3. User configures ASR options (model, GPU, language, output format).
4. User optionally enables translation and configures translation options.
5. User clicks Start; items process sequentially:
   - URL: download audio -> transcribe
   - File: transcribe
   - If translation enabled: translate ASR SRT output
6. UI shows current item index, status, and per-item errors; queue continues on failure.

## UI Layout (Single Page)
1. **Sources**
   - Multi-line text box for YouTube URLs (one per line)
   - “Select Audio Files” button (multi-select)
   - Queue list (type + path/URL)
2. **ASR Settings**
   - Whisper model path
   - Use GPU + backend
   - Language selection
   - Output format (SRT/TXT/JSON/Verbose)
3. **Translation (Optional)**
   - `Enable Translation` checkbox (default unchecked)
   - If enabled: target language, model, parallel requests, replace original, etc.
4. **Output**
   - Output directory or output naming rule
5. **Controls**
   - Start / Stop / Clear Queue
   - Progress indicator (current/total, status)

## Data Flow
- Build a unified in-memory queue of sources (URL or file path).
- For each item in queue (sequential):
  - If URL: download audio via existing downloader.
  - Run ASR via `ASRCoordinator`.
  - If translation enabled: pass ASR SRT output to legacy `TranslationThread`.
- Update UI progress and status after each phase.

## Error Handling
- Download failure: mark item failed, log error, continue.
- ASR failure: mark item failed, continue.
- Translation failure: keep ASR output, mark translation failed, continue.
- Stop: abort current and prevent further queue processing.

## Testing and Validation
Manual validation only for this iteration:
1. Batch URLs -> sequential download + transcribe.
2. Batch local audio files -> sequential transcribe.
3. Enable translation -> ASR output translated.
4. Failure in one item does not stop queue.
5. Stop halts queue processing.

## Trade-offs
- Using legacy `TranslationThread` keeps the feature working with minimal risk.
- Translation coordinator refactor is deferred to a later, separate task.
