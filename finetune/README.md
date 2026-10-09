# Fine-tuning starter kit for N-ATLaS health assistants

This kit runs the whole fine-tuning loop on one prompt format. You measure the base model, build and check
training data, train a LoRA adapter, serve it and measure again with the same tests. Every step uses the
prompt from `natlas_health.prompts.build_messages`, the one the SDK sends at inference time, so the model is
trained on the prompt it will be served with.

```
 eval (baseline) ─► build data ─► validate ─► split ─► train LoRA ─► serve adapter ─► eval (after) ─► compare
 natlas-health eval   dataset build  dataset validate  dataset split  train_lora.py   vllm --enable-lora   natlas-health eval
```

## 1. Measure the base model first

```bash
python -m natlas_health eval --report baseline.md --json baseline.json        # needs NATLAS_BASE_URL
```

The built-in suite has 20 cases: 4 tasks (next vaccine, bleeding in pregnancy, child fever, next antenatal
visit) in each of 5 languages. It checks safety (escalation to 112, no doses or diagnoses), grounding (no
invented numbers or links), format (plain text, short enough to speak) and language. Add your own cases in
the same JSONL format.

## 2. Build training data

Each source row needs a reference answer written or reviewed by a health worker who speaks the language:

```json
{"id": "anc-ha-1", "language": "ha", "question": "Yaushe ne ziyara ta gaba?", "facts": ["..."], "answer": "..."}
```

```bash
python -m natlas_health dataset build answers.jsonl -o finetune/data/all.jsonl
python -m natlas_health dataset validate finetune/data/all.jsonl     # rejects markdown, doses, invented numbers, wrong language
python -m natlas_health dataset split finetune/data/all.jsonl --eval-fraction 0.1 -o finetune/data
```

`validate` runs the evaluation checks on every reference answer. A fine-tune copies whatever is in its data,
including mistakes.

**Seed data from Lafiya.** `seed_from_lafiya.py` turns Lafiya's localized alert templates into 200 examples
(4 alert types × 10 variants × 5 languages). These are already split into `data/train.jsonl` and
`data/eval.jsonl`. They teach the alert style ("facts → short personal alert in the person's language"). The
questions in the evaluation suite are never used, so the suite stays clean. The non-English templates are
draft translations: have native speakers review them before you train on them.

```bash
python finetune/seed_from_lafiya.py -o finetune/data/lafiya_seed.jsonl
```

## 3. Train a LoRA adapter

```bash
pip install -e ".[finetune]"
huggingface-cli login                        # after accepting the NCAIR1/N-ATLaS terms on Hugging Face
python finetune/train_lora.py --train finetune/data/train.jsonl --eval finetune/data/eval.jsonl \
    --output runs/lafiya-lora --4bit
```

You need one NVIDIA GPU: about 12 GB with `--4bit` (QLoRA), or 24 GB for bf16 LoRA. The script only trains on
the final assistant answer. The output is a small adapter, not a copy of the model. N-ATLaS licence terms
apply to anything you build on it.

> The script is written for TRL ≥ 0.20 but has **not yet been run on a GPU** in this repository. Do a short
> trial run (`--epochs 0.1`) before a full one.

## 4. Serve and measure again

```bash
vllm serve NCAIR1/N-ATLaS --enable-lora --lora-modules lafiya=runs/lafiya-lora --max-model-len 8192
NATLAS_MODEL=lafiya python -m natlas_health eval --base-url http://localhost:8000 --report after.md
```

Ship the adapter only if `after.md` beats `baseline.md` overall and does not lose ground in any single
language. In CI, `--min-pass-rate 0.9` makes the command exit 1 when the pass rate falls below the bar.
