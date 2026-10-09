"""Fine-tuning data for N-ATLaS health assistants: build, validate and split chat-format JSONL.

Input: one case per line with a reference answer written (or reviewed) by a health worker / native speaker:

    {"language": "ha", "question": "...", "facts": ["..."], "guidance": ["..."], "answer": "..."}

Output: one training example per line in the "messages" format TRL, Axolotl and most trainers read. The system
prompt is built by ``prompts.build_messages`` - the exact prompt the SDK uses at inference time - so the model
learns the behaviour it will be asked for.

    python -m natlas_health dataset build answers.jsonl -o data/all.jsonl
    python -m natlas_health dataset validate data/all.jsonl
    python -m natlas_health dataset split data/all.jsonl --eval-fraction 0.1 -o data/
    # then: python finetune/train_lora.py --train data/train.jsonl --eval data/eval.jsonl
"""

import json
import random
from collections import Counter, defaultdict

from . import prompts
from .evaluate import check_reply
from .languages import LANGUAGES

# Format and safety checks every reference answer must pass; a fine-tune learns whatever is in the data.
REQUIRED_CHECKS = ("non_empty", "plain_text", "concise", "no_placeholders", "grounded_numbers", "safe_wording")


def read_jsonl(path):
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip() and not line.lstrip().startswith("//")]


def write_jsonl(path, rows):
    with open(path, "w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def make_example(language, facts, question, answer, guidance=None, assistant="Lafiya", id=None, history=None):
    messages = prompts.build_messages(language, facts, guidance, question=question, history=history, assistant=assistant)
    messages.append({"role": "assistant", "content": answer.strip()})
    example = {"language": language, "messages": messages}
    if id:
        example = {"id": id, **example}
    return example


def build(cases, assistant="Lafiya"):
    """Cases with an ``answer`` -> training examples. Cases without one are skipped."""
    return [
        make_example(c.get("language", "en"), c.get("facts", []), c.get("question"), c["answer"],
                     guidance=c.get("guidance"), assistant=assistant, id=c.get("id"), history=c.get("history"))
        for c in cases if c.get("answer")
    ]


def validate_example(example):
    """Return a list of problems (empty = OK)."""
    problems = []
    msgs = example.get("messages") or []
    lang = example.get("language")
    if lang not in LANGUAGES:
        problems.append(f"unknown language {lang!r}")
    if len(msgs) < 3 or msgs[0].get("role") != "system" or msgs[-1].get("role") != "assistant":
        problems.append("messages must be system, ..., user, assistant")
        return problems
    if msgs[-2].get("role") != "user":
        problems.append("the turn before the answer must be the user's")
    for m in msgs:
        if m.get("role") not in ("system", "user", "assistant") or not (m.get("content") or "").strip():
            problems.append(f"bad message {m!r:.80}")
    system = msgs[0]["content"]
    facts = system.split("FACTS:\n", 1)[1] if "FACTS:\n" in system else ""
    case = {"language": lang, "question": msgs[-2]["content"], "facts": [facts]}
    checks = check_reply(msgs[-1]["content"], case)
    for name in REQUIRED_CHECKS + ("language",):
        passed, detail = checks[name]
        if passed is False:
            problems.append(f"{name}: {detail}" if detail else name)
    return problems


def validate(examples):
    """{index: problems} for every example with problems."""
    return {i: p for i, ex in enumerate(examples) if (p := validate_example(ex))}


def split(examples, eval_fraction=0.1, seed=13):
    """Stratified by language: every language with 2+ examples appears in both splits. Returns (train, eval).

    eval_fraction=0 puts everything in train. A language with one example goes to train only.
    """
    groups = defaultdict(list)
    for ex in examples:
        groups[ex.get("language")].append(ex)
    rng = random.Random(seed)
    train, held = [], []
    for lang in sorted(groups, key=str):
        rows = groups[lang][:]
        rng.shuffle(rows)
        if eval_fraction <= 0 or len(rows) < 2:
            n_eval = 0
        else:  # at least one held out, at least one kept for training
            n_eval = min(len(rows) - 1, max(1, round(len(rows) * eval_fraction)))
        held += rows[:n_eval]
        train += rows[n_eval:]
    return train, held


def stats(examples):
    langs = Counter(ex.get("language") for ex in examples)
    chars = [len(ex["messages"][-1]["content"]) for ex in examples if ex.get("messages")]
    return {"examples": len(examples), "by_language": dict(langs),
            "answer_chars_avg": round(sum(chars) / len(chars)) if chars else 0}
