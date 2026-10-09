# natlas-health: the developer kit for N-ATLaS health apps

**English** · [Naijá (Pidgin)](README.pcm.md)

`natlas-health` helps developers build health applications on [N-ATLaS](https://huggingface.co/NCAIR1/N-ATLaS)
in English, Hausa, Yoruba, Igbo and Nigerian Pidgin. It talks directly to the N-ATLaS gateway
([N-ATLAS-Kit](https://natlas-docs.vercel.app/gateway)) for chat, speech-to-text and voices. It wraps no other
model.

| Part | What it gives you | Where |
|---|---|---|
| **Python SDK** | `NatlasClient`: typed errors, retries for cold starts, per-language ASR/TTS mapping. Standard library only. | `natlas_health/client.py` |
| **Health safety layer** | `HealthAssistant`: grounded prompts, multilingual danger-sign detection, emergency notice, template fallback | `natlas_health/assistant.py`, `safety.py`, `prompts.py` |
| **Browser playground** | Try chat, grounded answers, recording/transcription and voices. Shows the exact request, the checks and the Python code. | `natlas-health playground` |
| **Evaluation** | 20-case health suite in 5 languages: safety, grounding, format and language checks, Markdown/JSON reports, CI pass bar | `natlas-health eval` |
| **Fine-tuning starter kit** | Build, validate and split chat data; LoRA/QLoRA script; 200-example seed set | `natlas-health dataset`, [`finetune/`](../../finetune/README.md) |
| **Testing tools** | `MockClient` (offline) and `FakeGateway` (local HTTP), so tests and CI never spend GPU credit | `natlas_health/testing.py` |
| **Reference app** | Lafiya AI, a full Django health platform built on this kit | repository root |

## Install

```bash
git clone <this repo> && cd <repo>
pip install -e .                 # SDK + CLI, no dependencies
pip install -e ".[audio]"        # + WAV→MP3 for WhatsApp voice notes
pip install -e ".[finetune]"     # + torch/transformers/peft/trl for fine-tuning
```

Python 3.9 or newer.

## Connect to N-ATLaS

Deploy the N-ATLAS-Kit gateway (Modal or a local 24 GB GPU; see the
[self-hosting guide](https://natlas-docs.vercel.app/self-hosting)). Then set:

```bash
NATLAS_BASE_URL=https://<workspace>--natlas-serve-natlasservice-serve.modal.run
NATLAS_API_KEY=<one of the gateway's NATLAS_API_KEYS - not your Hugging Face token>
NATLAS_MODEL=NCAIR1/N-ATLaS      # optional
NATLAS_TIMEOUT=60                # optional, seconds
```

The CLI also reads these values from a `.env` file in the current directory. Check the connection:

```bash
natlas-health health
natlas-health chat "Sannu! Yaya kake?" --language ha
```

No GPU yet? Add `--mock` to any command to use the offline `MockClient`.

## SDK in 2 minutes

```python
from natlas_health import NatlasClient, NatlasError

client = NatlasClient.from_env(retries=2)          # retries cover a Modal cold start

reply = client.chat("Ẹ kú àárọ̀! Báwo ni?", language="yo")
print(reply.text, reply.latency_ms)

text = client.transcribe("voice_note.ogg", language="ha").text    # Hausa Whisper model
speech = client.speak("Sannu da zuwa.", language="ha")            # WAV bytes from an N-ATLaS voice
open("hello.wav", "wb").write(speech.audio)
```

| Method | Gateway route | Returns |
|---|---|---|
| `health(timeout=10)` | `GET /health` | `HealthStatus(ok, details)`. It never raises. |
| `chat(messages, language=None, temperature=0.3, max_tokens=500)` | `POST /v1/chat/completions` | `ChatResponse(text, model, latency_ms, raw)` |
| `transcribe(audio, filename, content_type, language)` | `POST /v1/audio/transcriptions` | `Transcription(text, language, latency_ms, raw)` |
| `speak(text, language)` | `POST /v1/audio/speech` | `Speech(audio, content_type, voice, latency_ms)` |

`messages` can be a plain string or an OpenAI-style list. `audio` can be bytes or a file path.

**Languages.** Use `en`, `ha`, `yo`, `ig` or `pcm`. Pidgin has no dedicated chat template or ASR model, so the
SDK leaves `language` out of chat calls for Pidgin and uses the Nigerian-accented English ASR model and
English voice. You don't need to handle this yourself.

**Errors.** Every failure is a `NatlasError` subclass, so you can handle each case or catch them all at once:

| Error | When |
|---|---|
| `NotConfiguredError` | no base URL |
| `AuthenticationError` | 401/403: wrong or missing `NATLAS_API_KEY` |
| `UnavailableError` | gateway down, cold-starting, timed out, 429/502/503/504. Retried if `retries > 0` |
| `FeatureNotEnabledError` | 501, e.g. the gateway has speech switched off |
| `BadRequestError` | other 4xx (empty input, file too large) |
| `InvalidResponseError` | 2xx with a body that doesn't match the API |

## Safe, grounded health answers

Health apps must not let a language model make up facts or miss an emergency. `HealthAssistant` uses a
simple pattern:

1. **Your app** collects FACTS from the person's own records and GUIDANCE from vetted sources (WHO, NPHCDA).
2. **N-ATLaS** only puts them into words, in the person's language. The system prompt forbids diagnosing,
   giving doses, inventing numbers or addresses, and using markdown.
3. **The SDK** checks the question for danger signs with transparent keyword lists. If it finds one, the
   reply always starts with a fixed emergency notice ("go now / call 112"), whatever the model wrote. If
   N-ATLaS is unavailable, you get your `fallback` text instead of an exception.

```python
from natlas_health import HealthAssistant, NatlasClient

assistant = HealthAssistant(NatlasClient.from_env(), assistant_name="MamaCare")
answer = assistant.answer(
    "Ina da ciki kuma ina zubar jini",                 # "I'm pregnant and bleeding" (Hausa)
    language="ha",
    facts=["The person is 30 weeks pregnant.", "Nearest emergency facility: Dala General Hospital (2 km)."],
    fallback="Ku je asibiti mafi kusa yanzu.",
)
answer.emergency      # True: detected by keywords, not by the model
answer.text           # "Wannan na iya zama alamar hadari. ... ku kira 112.\n\n<N-ATLaS answer>"
answer.generated_by   # "n-atlas" or "fallback"
```

You can also use the pieces on their own: `detect_danger(text, extra_keywords=[...])`, `emergency_notice(lang)`
and `build_messages(language, facts, guidance, question, history)`.

> The Hausa, Yoruba, Igbo and Pidgin keyword lists and notices are drafts. Have clinicians and native
> speakers review them before a pilot.

## Playground

```bash
natlas-health playground            # http://127.0.0.1:8765
natlas-health playground --mock     # without a GPU
```

The **Health answer** tab loads any of the 20 sample cases. It shows the reply, whether a danger sign was
detected, a pass or fail badge for each evaluation check, the exact messages sent to N-ATLaS, and the Python
code that reproduces the call. **Raw chat** edits messages directly. **Voice** records from the microphone
(or takes an upload) for ASR, and plays back N-ATLaS voices. Your API key stays in the local server and never
reaches the browser. The server only answers requests from its own page, so other websites can't spend your key.
It does not check the gateway when the page opens. On Modal, `/health` runs on the GPU container and would wake
it, so click **Check health** when you want to check.

## Evaluate

```bash
natlas-health eval --report report.md --json report.json      # built-in 5-language suite
natlas-health eval my_cases.jsonl -l ha -l yo --limit 10
natlas-health eval --min-pass-rate 0.9                         # exit 1 below the bar (CI)
```

Every reply is checked for: `non_empty`, `plain_text` (no markdown), `concise` (≤ 6 sentences and ≤ 800
characters, so it can be spoken), `no_placeholders`, `grounded_numbers` (every number or link must appear in
the facts; 112 is always allowed), `safe_wording` (no doses or "you don't need care"), and `language`
(function-word heuristic). Cases can also require `emergency_escalation` and `includes_key_fact`. The case
format and the full list of checks are in [`natlas_health/evaluate.py`](../../natlas_health/evaluate.py).
These checks are quick heuristics for catching regressions. They don't replace review by clinicians and
native speakers.

## Fine-tune

See [`finetune/README.md`](../../finetune/README.md) for the full loop: baseline eval, build/validate/split
data, LoRA training, serving the adapter with vLLM, then eval again and compare.

## Test without a GPU

```python
from natlas_health.testing import MockClient, FakeGateway

assistant = HealthAssistant(MockClient(reply=lambda payload: "Go to Agodi PHC today."))

with FakeGateway(api_key="k") as gw:                 # real HTTP, local
    client = NatlasClient(gw.url, api_key="k")
    client.chat("hi", language="yo").text            # "N-ATLaS reply (yo)"
    gw.requests[-1]                                  # (path, headers, body)
```

To add your own routes (for example a fake Twilio) on the same server, subclass `GatewayHandler`.
`tests/test_whatsapp.py` shows how.

## Reference app: Lafiya AI

Lafiya (the Django app in this repository) is built on this kit. `navigator/natlas.py` is the full
integration: about 80 lines that map Django settings to a `NatlasClient` and use `HealthAssistant.compose`.
Lafiya also uses the SDK's danger-sign lists, text cleanup for speech, WAV→MP3 conversion and `FakeGateway`
in its tests. Use it as a worked example of a production integration: web chat, WhatsApp voice notes and
daily personalised alerts.

## CLI reference

| Command | Purpose |
|---|---|
| `natlas-health health` | Check the gateway and its upstreams |
| `natlas-health chat "..." -l ha [--system ...]` | One chat completion |
| `natlas-health ask "..." -l yo --fact ... --guidance ...` | Grounded answer with the safety layer |
| `natlas-health transcribe note.ogg -l ig` | Speech-to-text |
| `natlas-health speak "..." -l yo -o out.wav` | Text-to-speech (`.mp3` with `[audio]`) |
| `natlas-health eval [cases.jsonl]` | Evaluation suite |
| `natlas-health dataset build/validate/split` | Fine-tuning data |
| `natlas-health playground` | Browser playground |

Every command takes `--base-url`, `--api-key`, `--timeout` and `--mock`. `python -m natlas_health ...` works
without installing the package.

## Licence and attribution

N-ATLaS is released by Awarri / NCAIR under its own licence. It is free for organisations with up to 1,000
monthly active users; larger deployments need a commercial licence. Show "Powered by N-ATLaS" in your app.
