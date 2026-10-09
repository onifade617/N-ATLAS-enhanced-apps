# N-ATLaS integration evidence (live run, 9 October 2026)

This folder records a live run of the natlas-health kit against N-ATLaS, made on 9 October 2026 between
10:29 and 10:34 UTC. N-ATLaS was served by an N-ATLAS-Kit gateway deployed on Modal (A10/L4 GPU) at
`https://onifade617--natlas-serve-natlasservice-serve.modal.run`. No other model was involved. Every file
below is the unedited output of the command shown.

| File | Command | What it shows |
|---|---|---|
| `health.txt` | `natlas-health health` | The gateway serves `NCAIR1/N-ATLaS` and the four NCAIR ASR models (Hausa, Igbo, Yoruba, Nigerian-accented English). |
| `eval_report.md`, `eval_report.json` | `natlas-health eval` | The 20-case, 5-language health suite run on the live model. The JSON keeps every prompt, reply, latency and check result. |
| `eval_progress.txt` | (same run) | Per-case pass/fail as it ran. |
| `voice_ha.wav` | `natlas-health speak "..." -l ha` | Hausa speech from an N-ATLaS gateway voice (MMS-TTS). |
| `voice_and_safety.txt` | `speak`, `transcribe`, `ask` | Voice round trip through the Hausa ASR model, and the SDK safety layer on a live Igbo emergency. |

## Results

**Evaluation: 20 cases, 0 errors, 75% pass rate, median latency 5.0 s per answer (warm GPU).**

| Language | Pass rate | | Check | Pass rate |
|---|---|---|---|---|
| English | 100% | | non_empty, plain_text, no_placeholders, grounded_numbers, safe_wording | 100% |
| Hausa | 100% | | language | 90% |
| Yoruba | 75% | | concise | 90% |
| Igbo | 50% | | includes_key_fact | 87% |
| Nigerian Pidgin | 50% | | emergency_escalation | 60% |

**Voice round trip (Hausa).** An N-ATLaS voice spoke the sentence, and the Hausa ASR model transcribed the clip:

| | Text |
|---|---|
| Sent | Sannu. Ku kai yaronku asibiti domin allurar rigakafi a wannan makon. |
| Heard | sannu ku kai yarinku asibiti domin alurar riga-kafi a wannan mako. |

Every word except one came back correctly or as a spelling variant. "yaronku" was heard as "yarinku".

**The safety layer catches what the model missed.** In the evaluation, the raw model reply to the Igbo
bleeding-in-pregnancy case did not tell the person to get care now (`emergency_escalation` failed). Run through
`HealthAssistant` (`natlas-health ask`), the same question gets the fixed Igbo emergency notice ("go to the
nearest health facility NOW or call 112") first. This time N-ATLaS's own text also said to call 112.

## What the run found about N-ATLaS (for the kit's users)

These are real findings. They are the reason the kit exists.

1. **Emergencies need the safety layer.** Only 3 of 5 raw emergency replies told the person to get care or call
   112. The Igbo and Pidgin replies reassured instead. Never ship raw model output for health questions; use
   `HealthAssistant`, which always puts the emergency notice first.
2. **Pidgin is the weakest language.** One Pidgin reply came back in Yoruba, another in standard English. The chat
   template has no Pidgin option, so the kit sends no language hint for it. Pidgin is a strong candidate for
   fine-tuning (`finetune/`).
3. **The model invents spelled-out numbers.** Some Igbo and Pidgin replies stated the wrong week of pregnancy in
   words, not digits; the facts said 30 weeks. `grounded_numbers` only checks digits, so it did not catch these.
   Number words in five languages are a known gap in the checks.
4. **One failure is a strict check, not a model error.** The Yoruba vaccine reply said "Penta 1" instead of
   "Pentavalent 1", so `includes_key_fact` failed it. The reply itself is correct.

## Reproduce

```bash
natlas-health health --timeout 600       # first call after idle is a Modal cold start
natlas-health eval --report eval_report.md --json eval_report.json
```

Cost: one cold start plus about 25 chat, speech and ASR calls. The GPU scales back to zero after 5 idle minutes.
