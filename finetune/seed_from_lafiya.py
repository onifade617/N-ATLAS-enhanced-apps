"""Turn Lafiya's localized templates into a seed fine-tuning set for N-ATLaS health alerts.

Lafiya's Intelligence Loop asks N-ATLaS to "write a short personal health alert from these facts". Its
hand-written templates (navigator/phrases.py) already say the same thing correctly in five languages, so
each (facts -> template) pair is a supervised example of the behaviour we want: grounded, short, plain
text, in the person's language. The questions in the evaluation suite are never used here, so the
eval set stays clean.

    python finetune/seed_from_lafiya.py -o finetune/data/lafiya_seed.jsonl
    python -m natlas_health dataset validate finetune/data/lafiya_seed.jsonl
    python -m natlas_health dataset split finetune/data/lafiya_seed.jsonl -o finetune/data

The non-English templates are draft translations: have native speakers review the output before training.
"""

import argparse
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from natlas_health import dataset  # noqa: E402
from navigator.phrases import PHRASES, phrase  # noqa: E402  (plain dicts, no Django needed)

CHILDREN = ["Tobi", "Amina", "Chidi", "Zainab", "Emeka", "Funmi", "Musa", "Ngozi", "Bola", "Ibrahim"]
VACCINES = [
    "Pentavalent 1, OPV 1, PCV 1 and Rotavirus 1", "Pentavalent 2, OPV 2, PCV 2 and Rotavirus 2",
    "Pentavalent 3, OPV 3, PCV 3 and IPV", "Measles 1 and Yellow Fever", "Measles 2 and Meningitis A",
]
DATES = ["14 Oct 2026", "21 Oct 2026", "3 Nov 2026", "17 Nov 2026", "1 Dec 2026", "12 Dec 2026"]
LGAS = ["Ibadan North", "Kano Municipal", "Enugu North", "Ikeja", "Maiduguri", "Port Harcourt", "Ilorin West"]
LEVELS = ["moderate", "high", "very_high"]


def examples_for(language, rng, n):
    out = []
    for i in range(n):
        child, vaccines, date = rng.choice(CHILDREN), rng.choice(VACCINES), rng.choice(DATES)
        lga, level, rising = rng.choice(LGAS), rng.choice(LEVELS), rng.random() < 0.5
        weeks = rng.randint(12, 36)
        contact = min(8, 1 + weeks // 5)
        t = PHRASES[language]
        hazard, level_word = t["hazards"]["malaria"], t["levels"][level]
        out += [
            {"id": f"vaccine-next-{language}-{i}", "language": language,
             "facts": [f"Child: {child}.", f"Next vaccines: {vaccines}, due on {date}."],
             "answer": phrase(language, "vaccine_next", child=child, vaccines=vaccines, date=date)},
            {"id": f"vaccine-overdue-{language}-{i}", "language": language,
             "facts": [f"Child: {child}.", f"Missed vaccines: {vaccines}, due since {date}.",
                       "Routine vaccines are free at public health facilities."],
             "answer": phrase(language, "vaccine_overdue", child=child, vaccines=vaccines, date=date)},
            {"id": f"anc-{language}-{i}", "language": language,
             "facts": [f"The person is {weeks} weeks pregnant.", f"Next antenatal visit: contact {contact} on {date}."],
             "answer": phrase(language, "pregnancy_status", weeks=weeks, n=contact, date=date)},
            {"id": f"malaria-risk-{language}-{i}", "language": language,
             "facts": [f"Malaria risk in {lga} is {level.replace('_', ' ')} this week" + (" and rising." if rising else "."),
                       "Advice: sleep under a treated net, clear standing water, test any fever at a clinic."],
             "answer": phrase(language, "risk", hazard=hazard, lga=lga, level=level_word,
                              trend=t["trend_rising"] if rising else "") + " " + t["malaria_advice"]},
        ]
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("-o", "--output", default="finetune/data/lafiya_seed.jsonl")
    p.add_argument("-n", "--per-language", type=int, default=10, help="variants per template per language")
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()
    rng = random.Random(args.seed)
    cases = list(itertools.chain.from_iterable(examples_for(lang, rng, args.per_language) for lang in PHRASES))
    examples = dataset.build(cases)
    problems = dataset.validate(examples)
    keep = [ex for i, ex in enumerate(examples) if i not in problems]
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    dataset.write_jsonl(args.output, keep)
    print(f"Wrote {len(keep)} examples to {args.output} ({len(problems)} dropped by validation)")
    for i, prob in list(problems.items())[:10]:
        print(f"  dropped {examples[i]['id']}: {'; '.join(prob)}")
    print(dataset.stats(keep))


if __name__ == "__main__":
    main()
