# UV Adoption Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Introduce uv as the recommended environment and execution workflow while preserving `requirements.txt` compatibility.

**Architecture:** Add Python project metadata (`pyproject.toml`) and a deterministic lock file (`uv.lock`) without changing runtime code. Update user-facing and maintainer-facing docs to promote uv first, with explicit pip fallback.

**Tech Stack:** Markdown docs, Python packaging metadata (`pyproject.toml`), uv.

---

### Task 1: Add uv project metadata

**Files:**
- Create: `pyproject.toml`
- Reference: `requirements.txt`

**Step 1: Define failing verification target**
Run: `Test-Path pyproject.toml`
Expected: `False`

**Step 2: Add minimal project metadata**
- Add name/version/requires-python
- Add dependencies equivalent to `requirements.txt`

**Step 3: Verify file exists**
Run: `Test-Path pyproject.toml`
Expected: `True`

### Task 2: Generate lock file with uv

**Files:**
- Create: `uv.lock`

**Step 1: Verify uv availability**
Run: `uv --version`
Expected: version output

**Step 2: Generate lock**
Run: `uv lock`
Expected: lock resolution success and `uv.lock` created

**Step 3: Validate lock file presence**
Run: `Test-Path uv.lock`
Expected: `True`

### Task 3: Update quick-start docs to recommend uv

**Files:**
- Modify: `README.md`
- Modify: `README_ZH.md`

**Step 1: Replace install/run primary path with uv**
- Use `uv sync` and `uv run python main.py`

**Step 2: Keep pip fallback**
- Keep `pip install -r requirements.txt` and `python main.py` as compatibility path

**Step 3: Verify docs mention both paths**
Run: `rg -n "uv sync|uv run python main.py|pip install -r requirements.txt" README.md README_ZH.md`
Expected: all patterns found in both files

### Task 4: Update technical docs for uv workflow

**Files:**
- Modify: `docs/TECHNICAL.md`
- Modify: `docs/TECHNICAL_ZH.md`

**Step 1: Add environment setup section for uv + pip fallback**
- Include exact commands

**Step 2: Update test command examples to uv-first**
- Example: `uv run pytest -v`

**Step 3: Verify technical docs mention uv commands**
Run: `rg -n "uv sync|uv run pytest|requirements.txt" docs/TECHNICAL.md docs/TECHNICAL_ZH.md`
Expected: all patterns found

### Task 5: End-to-end verification

**Files:**
- Verify: `pyproject.toml`, `uv.lock`, `README.md`, `README_ZH.md`, `docs/TECHNICAL.md`, `docs/TECHNICAL_ZH.md`

**Step 1: Sync environment via uv**
Run: `uv sync`
Expected: dependency environment synchronized

**Step 2: Run smoke test via uv**
Run: `uv run pytest tests/unit/test_smoke.py -v`
Expected: PASS

**Step 3: Sanity-check modified files**
Run: `git status --short`
Expected: only intended files changed
