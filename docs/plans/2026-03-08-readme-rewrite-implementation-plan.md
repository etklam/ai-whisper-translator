# README Rewrite Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rewrite quick-start README files and add complete bilingual technical documentation aligned with the current Python runtime architecture.

**Architecture:** Keep onboarding and maintenance concerns separated. README files become first-use guides only, while technical details move to dedicated docs under `docs/` with bilingual parity and code-aligned behavior descriptions.

**Tech Stack:** Markdown, Python runtime docs (`tkinter`, `pysrt`, `urllib`), Ollama local API.

---

### Task 1: Finalize quick-start English README

**Files:**
- Modify: `README.md`
- Reference: `main.py`, `src/main.py`, `src/gui/app.py`, `requirements.txt`

**Step 1: Draft quick-start structure**
- Create sections for prerequisites, installation, first-run workflow, key options, troubleshooting, and links.

**Step 2: Align commands with runtime**
- Use `pip install -r requirements.txt` and `python main.py`.
- Include Ollama model pull command and endpoint assumptions.

**Step 3: Validate option descriptions**
- Confirm names and behaviors against `src/gui/app.py`.

**Step 4: Save rewritten file**
- Replace existing README content with focused first-use content.

### Task 2: Finalize quick-start Traditional Chinese README

**Files:**
- Modify: `README_ZH.md`
- Reference: `README.md`

**Step 1: Mirror English structure in Traditional Chinese**
- Keep the same section order and practical flow.

**Step 2: Localize terminology for UI settings**
- Use current app wording for options and warnings.

**Step 3: Save rewritten file**
- Replace mixed-content README with quick-start only version.

### Task 3: Add full English technical documentation

**Files:**
- Create: `docs/TECHNICAL.md`
- Reference: `src/application/`, `src/domain/`, `src/infrastructure/`, `src/gui/`, `src/translation/`, `tests/`

**Step 1: Document scope and architecture**
- Explain active Python path and non-integrated TypeScript scaffolding.

**Step 2: Document module responsibilities and flow**
- Cover request lifecycle, progress events, prompt loading, and output handling.

**Step 3: Document reliability and testing**
- Include retry behavior, known limitations, and test execution command.

**Step 4: Save technical file**
- Ensure consistent headings and maintainability focus.

### Task 4: Add full Traditional Chinese technical documentation

**Files:**
- Create: `docs/TECHNICAL_ZH.md`
- Reference: `docs/TECHNICAL.md`

**Step 1: Translate and localize technical doc**
- Preserve technical precision and parity with English file.

**Step 2: Validate command snippets and paths**
- Keep commands unchanged while localizing surrounding text.

**Step 3: Save technical file**
- Ensure readability for maintainers preferring Chinese documentation.

### Task 5: Verify and cross-check documentation consistency

**Files:**
- Verify: `README.md`, `README_ZH.md`, `docs/TECHNICAL.md`, `docs/TECHNICAL_ZH.md`

**Step 1: Run docs presence check**
Run: `rg --files -g 'README*' docs/TECHNICAL*.md`
Expected: all four files listed.

**Step 2: Run key-term consistency checks**
Run: `rg -n "python main.py|OLLAMA|Auto Clean|取代原始檔案|TranslationCoordinator|tkinterdnd2" README.md README_ZH.md docs/TECHNICAL.md docs/TECHNICAL_ZH.md`
Expected: terms appear in correct contexts without contradiction.

**Step 3: Manual sanity review**
- Confirm quick-start docs do not include deep internal architecture details.
- Confirm technical docs include architecture, testing, limitations, and extension guidance.

**Step 4: Report completion**
- Provide concise summary and verification evidence.
