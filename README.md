# natlas-health: tools that make N-ATLaS easy to build with

**natlas-health** is a Nigerian-maintained, open-source developer kit for
[N-ATLaS](https://huggingface.co/NCAIR1/N-ATLaS). It takes developers from having access to the model to
**integrating, testing, adapting and deploying** it in English, Hausa, Yoruba, Igbo and Nigerian Pidgin, with
health applications as the first use case.

| Example solution in the challenge brief | What natlas-health provides | Docs |
|---|---|---|
| Python SDK with clean abstractions over N-ATLaS endpoints | `NatlasClient` and `HealthAssistant` | [SDK guide](docs/sdk/README.md) |
| Interactive browser-based playground for testing N-ATLaS outputs | `natlas-health playground` | [Playground](docs/sdk/README.md#playground) |
| Fine-tuning starter kit with training scripts and evaluation tools | `natlas-health eval`, `natlas-health dataset`, `finetune/train_lora.py` | [Fine-tuning](finetune/README.md) · [Evaluation](docs/sdk/README.md#evaluate) |
| Bilingual developer documentation with working examples | English and Nigerian Pidgin guides, runnable examples | [English](docs/sdk/README.md) · [Naijá](docs/sdk/README.pcm.md) |

## Direct N-ATLaS integration

Every call goes straight to the N-ATLaS gateway ([N-ATLAS-Kit](https://natlas-docs.vercel.app/gateway)):

- `NCAIR1/N-ATLaS` for chat;
- the NCAIR Hausa, Igbo, Yoruba and Nigerian-accented English speech-recognition models;
- the gateway's MMS-TTS voices.

No other model is wrapped or called anywhere in the code. The kit is built around how N-ATLaS works: its
chat-template `language` field, one speech-recognition model per language, and Pidgin routed to the English
models.

## Quick start

```bash
pip install "git+https://github.com/onifade617/N-ATLAS-enhanced-apps"
natlas-health ask "Which vaccine does my baby need next?" --fact "Child: Tobi, 6 weeks" --mock   # offline, no GPU
```

To call N-ATLaS for real, deploy the gateway on Modal or a 24 GB GPU
([self-hosting guide](https://natlas-docs.vercel.app/self-hosting)), then:

```bash
export NATLAS_BASE_URL=https://<workspace>--natlas-serve-natlasservice-serve.modal.run
export NATLAS_API_KEY=<one of the gateway's NATLAS_API_KEYS>
natlas-health health
natlas-health chat "Sannu! Yaya kake?" --language ha
```

## 1. Python SDK

```python
from natlas_health import NatlasClient, HealthAssistant

client = NatlasClient.from_env(retries=2)                         # retries cover Modal cold starts
client.chat("Ẹ kú àárọ̀! Báwo ni?", language="yo").text            # chat
client.transcribe("voice_note.ogg", language="ha").text           # speech-to-text (Hausa model)
client.speak("Sannu da zuwa.", language="ha").audio               # text-to-speech (WAV)

answer = HealthAssistant(client).answer(                          # grounded, safe health answer
    "Ina da ciki kuma ina zubar jini", language="ha",             # "I'm pregnant and bleeding"
    facts=["The person is 30 weeks pregnant."],
)
answer.text          # starts with the Hausa emergency notice ("... call 112"), whatever the model says
```

- **Clean abstractions:** typed errors (`AuthenticationError`, `UnavailableError`, …), mapping of each
  language to its speech and voice models, and no dependencies outside the Python standard library.
- **Safety layer for health:** answers are grounded in your app's facts, and danger signs are detected
  without relying on the model. A fixed emergency notice always comes first, and a fallback text is returned
  when N-ATLaS is unavailable.
- **Testing without a GPU:** `MockClient` (offline) and `FakeGateway`, which mirrors the real gateway's routes
  and errors.

## 2. Browser playground

```bash
natlas-health playground          # http://127.0.0.1:8765   (add --mock to try it without a GPU)
```

- Try chat, grounded health answers, microphone recording to speech-to-text, and N-ATLaS voices.
- See the exact request sent to N-ATLaS, pass/fail badges for the quality checks, and copy-ready Python code.
- Your API key stays on the local server, which only answers its own page.

## 3. Fine-tuning starter kit and evaluation tools

```bash
natlas-health eval --report report.md                         # 20 health cases × 5 languages
natlas-health dataset validate data.jsonl                     # rejects unsafe or ungrounded training answers
natlas-health dataset split data.jsonl -o finetune/data
python finetune/train_lora.py --train finetune/data/train.jsonl --eval finetune/data/eval.jsonl --4bit
```

- **Evaluation:** checks safety (escalation to 112, no doses), grounding (no invented numbers or links),
  format (plain text, short enough to speak) and language. It writes Markdown and JSON reports and can fail a
  CI build below a pass rate you set.
- **Fine-tuning:** a LoRA/QLoRA training script, plus 200 seed examples in 5 languages. Training, evaluation
  and inference all use the same prompt.

## 4. Bilingual developer documentation

- [English guide](docs/sdk/README.md) and [Nigerian Pidgin guide](docs/sdk/README.pcm.md). Every snippet runs
  as-is, or offline with `--mock`.
- [`examples/quickstart.py`](examples/quickstart.py) shows every feature in one file.

## Proof

- **Live N-ATLaS run** ([docs/evidence](docs/evidence/README.md), 9 Oct 2026):
  - 20 health cases, 0 errors, 75% pass rate (English and Hausa 100%);
  - a Hausa voice round trip;
  - the safety layer catching an emergency the raw model missed.
- **86 automated tests** (`python manage.py test tests`), none needing a GPU, plus a contract test against
  the real N-ATLAS-Kit gateway code.
- **Developer beta:** each tester gets their own key, and usage is measured from the gateway's
  content-free logs ([docs/beta](docs/beta/README.md)).
- **Deployed in a real app:** [Lafiya AI](docs/LAFIYA.md), a Django community-health platform with web chat,
  WhatsApp voice notes and daily alerts. It runs all its N-ATLaS calls through this kit, in about 80 lines
  ([`navigator/natlas.py`](navigator/natlas.py)).

## Project

- **Licence:** Apache-2.0 for the code ([LICENSE](LICENSE)). N-ATLaS and the datasets keep their own terms
  ([NOTICE](NOTICE)).
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md), especially language reviews from Hausa, Yoruba, Igbo
  and Pidgin speakers.
- **Changelog:** [CHANGELOG.md](CHANGELOG.md).
- **NAIC 2026 submission:** [docs/NAIC_PS01.md](docs/NAIC_PS01.md).
- **Architecture:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
