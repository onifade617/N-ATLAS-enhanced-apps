# natlas-health beta: tester guide

Thank you for testing **natlas-health**, an open developer kit for building health apps on
[N-ATLaS](https://huggingface.co/NCAIR1/N-ATLaS), Nigeria's multilingual language model. It covers English,
Hausa, Yoruba, Igbo and Pidgin. Your job is to try it like a developer would and tell us honestly where it is
hard. Finding problems is the point.

**Time:** about 90 minutes. **You need:** Python 3.9 or newer and a terminal. A microphone is optional
(task 4). **Your tester id** (e.g. `T03`) and **API key** come to you privately from the organiser.

**Privacy and safety:**
- The N-ATLaS gateway logs only *which feature and language* you used and how long it took, under a
  fingerprint of your key. It never logs your prompts, replies or audio.
- Use **made-up** people and data only. This is a developer test, not medical advice.
- Don't share your key. It stops working after the beta.

**Write down the time** when you start each task and when it works, and note anything confusing. The form
at the end asks for this.

---

## Task 1: install and run offline (no key needed)

```bash
pip install "git+https://github.com/onifade617/N-ATLAS-enhanced-apps"
#   or, if you were sent a .whl file:  pip install natlas_health-0.1.0-py3-none-any.whl
natlas-health --version
natlas-health ask "Which vaccine does my baby need next?" --fact "Child: Tobi, 6 weeks" --mock
```

`--mock` uses an offline fake, so nothing reaches N-ATLaS yet. Docs: [English](../sdk/README.md) ·
[Naijá](../sdk/README.pcm.md).

## Task 2: your first real N-ATLaS call

```bash
# macOS/Linux                                   # Windows PowerShell
export NATLAS_BASE_URL=<url from organiser>      $env:NATLAS_BASE_URL="<url>"
export NATLAS_API_KEY=<your key>                 $env:NATLAS_API_KEY="<your key>"

natlas-health health --timeout 600
natlas-health chat "Greet me in one sentence." --language yo     # try your own language: ha, yo, ig, pcm, en
```

If `health` waits a while, the GPU is waking up (a "cold start", up to a few minutes). That's normal. Tell us
if the message you saw didn't explain it.

## Task 3: a safe, grounded health answer in Python

Save this as `try_it.py`, change the language, question and facts, and run it:

```python
from natlas_health import NatlasClient, HealthAssistant

assistant = HealthAssistant(NatlasClient.from_env())
answer = assistant.answer(
    "When is my next antenatal visit?",            # try asking in Hausa, Yoruba, Igbo or Pidgin
    language="en",
    facts=["The person is 25 weeks pregnant.", "Next antenatal visit: 20 Oct 2026 at Dala PHC (0.8 km)."],
)
print(answer.text)
print(answer.generated_by, answer.emergency)
```

Then ask about a **danger sign**, e.g. "I am pregnant and bleeding" (or in your language). Check that the
reply starts with an emergency notice. Does the rest of the answer make sense?

## Task 4: the playground

```bash
natlas-health playground          # open http://127.0.0.1:8765
```

- **Health answer:** load a sample case in your language and press *Ask N-ATLaS*. Look at the check badges
  and "Request sent to N-ATLaS".
- **Voice:** record yourself asking a short question (mic), then press *Speak* to hear a reply voice.
- Copy the **Python** snippet it shows. Does it run as-is?

## Task 5: build something small (20–40 minutes)

Pick one, or invent your own:

- a FastAPI/Flask/Django endpoint `POST /ask` that answers a health question with `HealthAssistant`;
- a command-line "vaccine reminder" that reads a child's details and writes the message in Hausa or Yoruba;
- a script that transcribes a voice note (`client.transcribe("note.ogg", language="ha")`) and answers it.

Share a gist or repo link in the form. It doesn't have to be pretty.

## Task 6: evaluate

```bash
natlas-health eval --language yo --language pcm --report my_eval.md     # pick 1–2 languages (about 8 calls)
```

Read the failures in `my_eval.md`. Do you agree with them? Then write **2 new test cases** in your language,
in the same format as the lines in
[`health_eval.jsonl`](../../natlas_health/data/health_eval.jsonl), and paste them into the form.

## Task 7 (fluent speakers of Hausa, Yoruba, Igbo or Pidgin): language review

Pick what matches your language and note anything wrong or unnatural:

- the questions for your language in `natlas_health/data/health_eval.jsonl`;
- the emergency message and danger-sign words in `natlas_health/safety.py`;
- for Pidgin: [docs/sdk/README.pcm.md](../sdk/README.pcm.md).

## Finally: the feedback form (10 min)

Fill the form the organiser sent, using your tester id. Report bugs there or as a GitHub issue. Copy any
error text exactly.

Budget: please stay under about 150 requests. The GPU is paid for by a small team.
