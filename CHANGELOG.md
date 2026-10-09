# Changelog

All notable changes to natlas-health. Dates are in WAT.

## [0.1.0] - 2026-10-09

First release of the developer kit, with Lafiya AI as its reference app.

### Added
- **SDK:** `NatlasClient`.
  - Chat, speech-to-text, text-to-speech and health checks against the N-ATLAS-Kit gateway.
  - Typed errors and cold-start retries.
  - Mapping of Pidgin to the English speech and voice models.
  - Standard library only.
- **Safety layer:** `HealthAssistant`.
  - Grounded prompts built from your app's facts.
  - Multilingual danger-sign detection.
  - A fixed emergency notice in 5 languages, put before any model reply.
  - A fallback text when N-ATLaS is unavailable.
- **Playground:** `natlas-health playground`.
  - Chat, grounded answers, microphone speech-to-text and voices.
  - Shows the exact request sent, the evaluation checks and the equivalent Python code.
  - Answers only requests from its own page.
- **Evaluation:** `natlas-health eval`, a 20-case, 5-language health suite.
  - Checks safety, grounding, format and language.
  - Writes Markdown and JSON reports; `--min-pass-rate` sets a CI pass bar.
- **Fine-tuning kit:**
  - `natlas-health dataset build/validate/split` for training data.
  - `finetune/train_lora.py` for LoRA/QLoRA training, with an fp16 fallback for older GPUs.
  - 200 seed examples built from Lafiya's templates.
- **Testing:** `MockClient` and `FakeGateway`, which mirror the real gateway's routes and error format.
- **Docs:** developer documentation in English and Nigerian Pidgin, `examples/quickstart.py`, and a beta
  programme kit (`docs/beta/`, `scripts/beta/`).
- **Evidence:** a live-gateway run, kept in `docs/evidence/`.

### Changed
- Lafiya's N-ATLaS integration (`navigator/natlas.py`) now runs entirely through the SDK.
