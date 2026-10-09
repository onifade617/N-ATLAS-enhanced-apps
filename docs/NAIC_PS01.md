# NAIC 2026: natlas-health submission (Problem Statement 01, Developer Infrastructure)

**Deadline: 12 October 2026, 11:59 PM WAT.**

> *Build the tools that make N-ATLAS easy to build with.* The challenge asks for Nigerian-maintained tooling that
> helps developers move from accessing the model to integrating, testing, adapting and deploying it.
> **Key requirement:** the solution must directly integrate with N-ATLAS. Wrapping another general-purpose model
> does not qualify.

**Pitch.** `natlas-health` is the N-ATLaS developer kit for health. One install gives developers a Python SDK for
the N-ATLaS gateway, a safety layer for health answers, a browser playground, a five-language health evaluation
suite and a fine-tuning starter kit. Lafiya AI, a full community-health platform, is the reference app that
shows the kit working in production.

## Challenge examples → what we built

| Example solution in the brief | natlas-health | Evidence |
|---|---|---|
| Python or JavaScript SDK with clean abstractions over N-ATLAS endpoints | `NatlasClient`: `chat` / `transcribe` / `speak` / `health`, typed errors, cold-start retries, language mapping (Pidgin → English ASR/TTS); `HealthAssistant` for grounded, safe answers; standard library only | `natlas_health/`, `tests/test_sdk.py` |
| Interactive browser-based playground for testing N-ATLAS outputs | `natlas-health playground`: chat, grounded answers, mic → ASR, TTS playback, exact request, eval check badges, Python code export; the key stays server-side | `natlas_health/playground.py` |
| Fine-tuning starter kit with training scripts and evaluation tools | `natlas-health dataset build/validate/split`, `finetune/train_lora.py` (LoRA/QLoRA), 200-example seed set from Lafiya's 5-language templates, `natlas-health eval` before/after with a CI pass bar | `finetune/`, `natlas_health/evaluate.py` |
| Bilingual developer documentation with working examples | English and Nigerian Pidgin guides; every snippet runs with `--mock` | `docs/sdk/README.md`, `docs/sdk/README.pcm.md`, `examples/quickstart.py` |

## Key requirement: direct N-ATLaS integration

- Every model call goes to the N-ATLaS gateway (N-ATLAS-Kit): `NCAIR1/N-ATLaS` for chat, the NCAIR Hausa, Igbo,
  Yoruba and Nigerian-accented English ASR models, and its MMS-TTS voices. No other LLM, ASR or TTS provider
  appears anywhere in the code.
- The prompts, the language mapping and the evaluation suite are built around N-ATLaS: its chat-template
  `language` field, its per-language ASR models and its voices.
- The kit is open, Nigerian-maintained and health-specific. It fills the gap between "the model is downloadable"
  and "my clinic app is safe to ship".

## Submission checklist

| Item | Status |
|---|---|
| Working artefact: repository with SDK, CLI, playground, eval, fine-tuning kit, reference app | ✅ built; 86 automated tests pass without a GPU, plus a contract run against the real N-ATLAS-Kit gateway code (GPU parts stubbed) |
| N-ATLaS integration evidence: live gateway health, 5-language eval, voice round trip, safety layer | ✅ [docs/evidence/](evidence/README.md), 9 Oct 2026: 20 cases, 0 errors, 75% pass (EN/HA 100%) |
| Technical documentation | ✅ `docs/sdk/`, `finetune/README.md`, `docs/ARCHITECTURE.md` |
| Developer beta with real users | ⚠️ ready: [tester guide](beta/TESTER_GUIDE.md), per-tester keys and usage report (`scripts/beta/`); run 10–11 Oct |
| Bilingual docs reviewed by a fluent Pidgin speaker | ⚠️ draft; needs review | (assign to beta task 7) |
| Native-speaker review of the Hausa/Yoruba/Igbo eval questions, keywords and seed data | ⚠️ draft; needs review |
| LoRA training run | ❌ not run (needs a GPU); the script is written but untested |
| 3–5 minute video | ❌ to record (outline below) |
| Team profile, registration | ❌ team to provide |

**Ask the Secretariat (naic@nitda.gov.ng):** whether the team can switch from PS02 to PS01, and whether team
members employed by N-ATLaS partner organisations are eligible.

## Video outline (3–5 min)

1. **Problem (30 s).** N-ATLaS can be downloaded, but building a safe health app on it in five languages takes
   weeks of plumbing.
2. **Install and SDK (45 s).** `pip install -e .`, `natlas-health health`, then three lines of Python for chat,
   transcription and speech in Hausa.
3. **Playground (60 s).** Load the Yoruba "bleeding in pregnancy" case. The danger sign is caught, the emergency
   notice comes first, and the check badges and exact request are shown. Record a voice note, transcribe it,
   play the reply in an N-ATLaS voice.
4. **Evaluation (45 s).** `natlas-health eval`: pass rate by language and by check, with failures explained.
5. **Fine-tuning (30 s).** `dataset validate` rejects an unsafe training answer; split; the LoRA command.
6. **Proof in production (45 s).** Lafiya's whole integration is about 80 lines on the kit. Show a WhatsApp voice
   note answered in Igbo.
7. **Close (15 s).** Open source, Nigerian-maintained, bilingual docs. Next steps: a JavaScript SDK and more
   sectors.
