# UV Adoption Design (Keep requirements.txt Compatibility)

## Context
The project currently uses `requirements.txt` + `pip` instructions in docs. The user wants uv added as the recommended workflow while preserving `requirements.txt` compatibility.

## Goals
- Add first-class uv project metadata and lock file.
- Keep `requirements.txt` working for existing users.
- Make README recommend uv by default.
- Keep runtime behavior unchanged.

## Non-Goals
- No refactor of application code.
- No removal of `requirements.txt`.
- No packaging pipeline redesign.

## Design
1. Add `pyproject.toml` with minimal metadata:
   - project name/version
   - Python requirement matching runtime expectations
   - dependencies equivalent to `requirements.txt`
2. Generate `uv.lock` from `pyproject.toml`.
3. Update quick-start docs (`README.md`, `README_ZH.md`):
   - primary install path: `uv sync`
   - primary run path: `uv run python main.py`
   - fallback path: `pip install -r requirements.txt` + `python main.py`
4. Update technical docs (`docs/TECHNICAL.md`, `docs/TECHNICAL_ZH.md`) with uv workflow and test command examples.

## Risks and Mitigations
- uv might be unavailable in environment:
  - keep pip fallback documented and untouched.
- lock generation may fail due network:
  - retry with elevated permissions if sandbox blocks package index access.

## Success Criteria
- `pyproject.toml` and `uv.lock` exist and are valid.
- `uv sync` succeeds.
- `uv run python main.py --help` is not applicable (GUI app), so verification uses unit test smoke command.
- README recommends uv while preserving pip compatibility instructions.
