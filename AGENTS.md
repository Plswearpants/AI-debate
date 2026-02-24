# AGENTS.md

## Cursor Cloud specific instructions

### Overview

This is a Python CLI-based **AI Debate Platform** that simulates structured debates between AI agents. There is no web UI, no database, no Docker — it's a pure Python application that calls external LLM APIs (via OpenRouter or direct API keys).

### Running commands

- Use `python3` (or `python` if the symlink exists) for all commands. The VM may not have a `python` symlink by default — create one with `sudo ln -sf /usr/bin/python3 /usr/bin/python` if needed.
- Installed scripts (`pytest`, `flake8`, `black`, `mypy`) land in `~/.local/bin`. Ensure `PATH` includes `$HOME/.local/bin`.

### Lint / Test / Build / Run

| Task | Command |
|------|---------|
| Lint (flake8) | `flake8 src/ --max-line-length=120` |
| Format check | `black --check src/ tests/` |
| Tests | `pytest tests/ -v` |
| Config verify | `python verify_model_config.py` |
| Run debate | `python run_debate.py "Topic here"` |
| Resume debate | `python resume_debate.py <debate-id>` |

See `README.md` for full usage examples and `CONTRIBUTING.md` for development guidelines.

### Pre-existing test failures

9 of 154 unit tests fail on the current `main` codebase (as of Jan 2026) due to test fixture mismatches (`KeyError: 'description'`, `KeyError: 'persona_type'`, `KeyError: 'round_number'`, and `Mock` serialization issues). These are not environment issues — they are pre-existing test bugs. The other 145 tests pass reliably.

### API keys

Running a full debate requires an `OPENROUTER_API_KEY` (or individual Gemini/Claude/Perplexity keys). Unit tests do **not** require API keys — they mock all external calls. Set keys in `.env` (copy from `env.example`).

### Flake8 warnings

The codebase has many pre-existing `W293` (blank line contains whitespace) and `E501` (line too long) warnings. These are in the existing code and are not blockers.
