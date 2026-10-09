# natlas-health: developer kit for N-ATLaS health app

[English](README.md) · **Naijá (Pidgin)**

> Dis na draft Pidgin translation. Abeg make person wey sabi Naijá well-well check am before we publish am.
> Code and command no change: na di same for both language.

`natlas-health` dey help developer build health app on top [N-ATLaS](https://huggingface.co/NCAIR1/N-ATLaS)
for English, Hausa, Yoruba, Igbo and Pidgin. E dey yarn direct with di N-ATLaS gateway
([N-ATLAS-Kit](https://natlas-docs.vercel.app/gateway)) for chat, speech-to-text and voice. E no dey use any
oda model.

| Wetin | Wetin e go do for you | Where e dey |
|---|---|---|
| **Python SDK** | `NatlasClient`: clear error, retry when gateway dey wake up, e sabi which ASR/voice each language need. Na only Python standard library. | `natlas_health/client.py` |
| **Health safety layer** | `HealthAssistant`: grounded prompt, e dey catch danger sign for 5 language, emergency message, fallback | `natlas_health/assistant.py` |
| **Playground for browser** | Try chat, health answer, record voice, hear di voice. E go show you di exact request and di Python code. | `natlas-health playground` |
| **Evaluation** | 20 test case for 5 language: safety, grounding, format and language check | `natlas-health eval` |
| **Fine-tuning starter kit** | Build, check and split data; LoRA script; 200 seed example | `natlas-health dataset`, [`finetune/`](../../finetune/README.md) |
| **Testing tools** | `MockClient` and `FakeGateway`: your test no go chop GPU money | `natlas_health/testing.py` |
| **Reference app** | Lafiya AI: full Django health app wey use dis kit | root of di repo |

## How to install am

```bash
pip install -e .                 # SDK + CLI, e no need any oda package
pip install -e ".[audio]"        # + WAV→MP3 for WhatsApp voice note
pip install -e ".[finetune]"     # + torch/transformers/peft/trl for fine-tuning
```

You need Python 3.9 or newer.

## How to connect to N-ATLaS

Deploy di N-ATLAS-Kit gateway first (Modal or your own 24 GB GPU; see di
[self-hosting guide](https://natlas-docs.vercel.app/self-hosting)). After that, put dis one for `.env`:

```bash
NATLAS_BASE_URL=https://<workspace>--natlas-serve-natlasservice-serve.modal.run
NATLAS_API_KEY=<one of di gateway NATLAS_API_KEYS - no be your Hugging Face token>
```

Check say e dey work:

```bash
natlas-health health
natlas-health chat "How far? Wetin dey happen?" --language pcm
```

You never get GPU? Add `--mock` to any command and e go use di offline `MockClient`.

## SDK for 2 minutes

```python
from natlas_health import NatlasClient, NatlasError

client = NatlasClient.from_env(retries=2)          # retry na for when Modal dey wake up (cold start)

reply = client.chat("Ẹ kú àárọ̀! Báwo ni?", language="yo")
print(reply.text, reply.latency_ms)

text = client.transcribe("voice_note.ogg", language="ha").text    # Hausa ASR model
speech = client.speak("Sannu da zuwa.", language="ha")            # WAV from N-ATLaS voice
open("hello.wav", "wb").write(speech.audio)
```

**Language:** `en`, `ha`, `yo`, `ig`, `pcm`. Pidgin no get im own chat template or ASR model, so di SDK go
use di Nigerian-accented English ASR model and English voice. You no need do anything.

**Error:** every wahala na `NatlasError`. If e be `AuthenticationError`, your key no correct. If e be
`UnavailableError`, di gateway dey sleep or e don down: wait small or use your fallback.
`FeatureNotEnabledError` mean say di gateway no on dat feature (like voice).

## Health answer wey safe and grounded

Health app no fit allow AI model to cook up fact or miss emergency. Na so `HealthAssistant` dey work:

1. **Your app** go bring di FACTS (from di person record) and GUIDANCE (from WHO, NPHCDA).
2. **N-ATLaS** go just talk dem for di person language. Di system prompt no allow am diagnose, give drug
   dose, cook up number or address, or use markdown.
3. **Di SDK** go check di question for danger sign. If e see one, di answer go always start with
   emergency message ("go hospital now / call 112"), no matter wetin di model talk. If N-ATLaS no dey
   available, you go get your `fallback`, no be exception.

```python
from natlas_health import HealthAssistant, NatlasClient

assistant = HealthAssistant(NatlasClient.from_env())
answer = assistant.answer(
    "I get belle and blood dey come out for my body",
    language="pcm",
    facts=["The person is 30 weeks pregnant.", "Nearest emergency facility: General Hospital (3 km)."],
    fallback="Go the nearest hospital now.",
)
answer.emergency      # True: na keyword catch am, no be di model
answer.text           # "This fit be danger sign. Go the nearest hospital NOW or call 112.\n\n<N-ATLaS answer>"
answer.generated_by   # "n-atlas" or "fallback"
```

> Di Hausa, Yoruba, Igbo and Pidgin keyword list na draft. Make doctor and people wey sabi di language
> check dem before una go pilot.

## Playground

```bash
natlas-health playground            # http://127.0.0.1:8765
natlas-health playground --mock     # if you no get GPU
```

For di **Health answer** tab, you fit load any of di 20 sample case. E go show di answer, if e catch danger
sign, badge for each check (✓/✗), di exact message wey e send go N-ATLaS, and di Python code. **Raw chat**
na for any message. **Voice** go record from your mic for ASR, and e go play N-ATLaS voice back. Your API key
dey only for di local server: e no dey reach di browser. Na only di playground page fit use am, so oda website no
fit spend your key. E no dey check di gateway when di page open, because for Modal, `/health` go wake di GPU.
Press **Check health** when you wan check am.

## Evaluation

```bash
natlas-health eval --report report.md                # di 5-language suite wey dey inside
natlas-health eval my_cases.jsonl -l pcm -l ha
natlas-health eval --min-pass-rate 0.9               # for CI: e go fail if e no reach 90%
```

Di check dem: answer no empty, no markdown, e short reach to read am aloud, no placeholder like `[address]`,
every number must dey inside di facts (112 dey allowed), no drug dose, di correct language, and for
emergency case e must talk "112". Dem be quick check to catch wahala early: dem no fit replace doctor and
people wey sabi di language.

## Fine-tuning

Check [`finetune/README.md`](../../finetune/README.md): first eval (baseline), build data, check am, split
am, train LoRA, serve am with vLLM, then eval again and compare di two.

## Test without GPU

```python
from natlas_health.testing import MockClient, FakeGateway

assistant = HealthAssistant(MockClient(reply=lambda payload: "Go Agodi PHC today."))

with FakeGateway(api_key="k") as gw:
    client = NatlasClient(gw.url, api_key="k")
    client.chat("How far?", language="pcm").text
```

## Lafiya AI (reference app)

Lafiya (di Django app for dis repo) na wetin we build with dis kit. `navigator/natlas.py` na di full
integration: about 80 lines. Na example of how to use di kit for real app: web chat, WhatsApp voice note
and daily alert.

## Licence

Awarri / NCAIR na im release N-ATLaS under im own licence. E free for organisation wey get up to 1,000 user
every month; if una pass dat one, una go need commercial licence. Make your app show "Powered by N-ATLaS".
