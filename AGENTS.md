## Local Voice Chat Agent – Agent Playbook

### Project Overview

- Fully local push-to-talk voice assistant: microphone → Whisper (ASR) → Ollama mistral:latest → Piper (TTS) → speakers.
- **New Architecture**: Modular `levial` package structure.
- `PRD` documents scope, requirements, and roadmap. Keep it aligned with new features/configs.

### Build & Test Commands

| Purpose               | Command                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| Build Whisper backend | `cd whisper.cpp && cmake -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j` |
| Install Python deps   | `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt` |
| **Run Levial**        | `source .venv/bin/activate && python -m levial.main`                                    |
| Piper smoke test      | `echo "Hello"                                                                           | piper --model en_US-lessac-medium.onnx --output_file test.wav` |

### Configuration Layer

- Config lives in `config/default.json`. Key fields:
  - `active_profile`: default profile name (can override with `LVCA_PROFILE` env).
  - `profiles.<name>`: per-profile model choices (`llm_model`, `whisper_model`, `piper_model`), audio settings, temperature, history caps.
  - `wake_word`, `timeouts`, `artifacts_dir`.
- Override config file path via `LVCA_CONFIG=/path/to/custom.json`.
- Example to run snappy profile: `LVCA_PROFILE=snappy python -m levial.main`.

### Runtime Requirements

- `whisper.cpp/build/bin/whisper-cli` plus `whisper.cpp/models/ggml-small.bin`.
- `ollama serve` running locally; `ollama pull mistral:latest`.
- Piper voice model `en_US-lessac-medium.onnx` in repo root.
- macOS: ensure `afplay` is available (default). Linux: install `ffplay`.

### Coding Guidelines

- **Package Structure**:
  - `levial/config.py`: Configuration management.
  - `levial/orchestrator.py`: Main state machine.
  - `levial/audio.py`, `asr.py`, `tts.py`, `llm.py`: Provider wrappers.
- Prefer config-driven behavior over hard-coded constants.
- Log key steps (recording start, transcription result, LLM response, TTS completion).

### Testing Instructions

- Run `python -m levial.main`, verify end-to-end audio roundtrip.
- Smoke test subsystems individually when debugging:
  1. Whisper: `DYLD_LIBRARY_PATH=... ./whisper.cpp/build/bin/whisper-cli -m whisper.cpp/models/ggml-small.bin -f test.wav -otxt`.
  2. Piper: pipe sample text and listen to output WAV.
  3. Ollama: `ollama run mistral:latest "Say hello"`.

### Security & Privacy Notes

- All inference stays local; do not introduce external API calls without explicit opt-in.
- Avoid logging raw transcripts/responses beyond artifacts needed for debugging.
- Keep `artifacts/` out of version control if they contain sensitive audio/text.

### Workflow & Automation Rules

Whenever code changes are made:

1. **Update configuration/PRD**: reflect any new behavior or dependencies in `PRD` and `AGENTS.md`.
2. **Re-run subsystem tests**: Whisper CLI, Piper TTS, Ollama mistral:latest prompts.
3. **Verify full loop**: execute `python -m levial.main` and confirm microphone → TTS roundtrip.
4. **Document instructions**: append any new steps or gotchas to `AGENTS.md` immediately.

### Extra Guidelines

- Commit messages: use `feat:`, `fix:`, `docs:`, etc., and mention affected subsystem (e.g., `feat: add wake-word config hook`).
- Pull requests: include reproduction steps and describe how you tested mic/ASR/LLM/TTS.
- Deployment: no cloud deployment yet; MVP is local-only. Keep scripts portable between macOS + Linux where possible.
