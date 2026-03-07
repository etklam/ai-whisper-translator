# README Rewrite Design (Quick Start + Technical Docs)

## Context
The repository currently has two README files with uneven depth and mixed audience targets. The goal is to separate first-time user onboarding from maintainer-focused technical details.

## Goals
- Keep both README files focused on first-time user quick start.
- Add complete technical documentation in both English and Traditional Chinese.
- Keep terminology and behavior aligned with the current Python runtime code.

## Non-Goals
- No runtime behavior changes.
- No packaging pipeline changes.
- No test or feature implementation changes.

## Information Architecture
- `README.md`: English quick start only.
- `README_ZH.md`: Traditional Chinese quick start only.
- `docs/TECHNICAL.md`: Full technical documentation in English.
- `docs/TECHNICAL_ZH.md`: Full technical documentation in Traditional Chinese.

## README Content Boundaries
Both README files will include:
1. What the tool does
2. Prerequisites
3. Install and run commands
4. First translation workflow
5. Key options explanation
6. Output and backup rules
7. Quick troubleshooting
8. Links to technical docs

Both README files will exclude:
- Deep architecture details
- Internal module responsibilities
- Detailed testing strategy
- Packaging internals

## Technical Doc Coverage
Both TECHNICAL files will include:
1. Scope and current state
2. Architecture and module responsibilities
3. End-to-end translation flow
4. Config and defaults
5. Error handling and retry behavior
6. Testing strategy and commands
7. Packaging notes
8. Known limitations and extension points

## Alignment Decisions
- Primary runtime entry remains `python main.py`.
- Ollama endpoint remains `http://localhost:11434/v1/chat/completions`.
- `tkinterdnd2` remains optional and explicitly documented.
- TypeScript files in `src/*.ts` are documented as non-integrated scaffolding.

## Success Criteria
- A first-time user can complete one translation using README only.
- A maintainer can understand architecture and extension points using TECHNICAL docs.
- No contradictions between docs and current code paths.
