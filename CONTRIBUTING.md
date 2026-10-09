# Contributing to natlas-health

Contributions are welcome, especially from speakers of Hausa, Yoruba, Igbo and Nigerian Pidgin, and from
health workers.

## Most wanted

1. **Language review.** Check the draft translations and suggest fixes:
   - evaluation questions in `natlas_health/data/health_eval.jsonl`;
   - danger-sign keywords and emergency notices in `natlas_health/safety.py`;
   - Lafiya's templates in `navigator/phrases.py`;
   - the Pidgin docs.
2. **Evaluation cases.** Add realistic health questions in your language to `health_eval.jsonl`. Use
   synthetic facts only.
3. **Clinical review.** Check the safety rules in `natlas_health/prompts.py` and the guidance in
   `navigator/knowledge.py` against WHO and NPHCDA guidelines.
4. **Bug reports.** Open a GitHub issue with the command you ran, the full error text and your OS and Python
   version. Never include your API key.

## Development

```bash
pip install -e .
python manage.py test tests          # Lafiya + SDK tests; no GPU or network needed
python -m natlas_health eval --mock  # wiring check without a GPU
```

- The SDK (`natlas_health/`) must stay **standard-library only** and must not import Django.
- Every change to gateway behaviour needs a test against `natlas_health.testing.FakeGateway`, and should
  match the real gateway code in N-ATLAS-Kit (`serve/natlas_serve/gateway.py`).
- Tests must never call a real gateway; it costs GPU credit.
- Keep one prompt for everything: change `natlas_health/prompts.py`, not copies of it.
- **Safety rules are not optional.** A change that lets a model reply skip the emergency notice when a danger
  sign is present will not be merged.

## Data and privacy

Use synthetic data only. Never commit real patient data, `.env`, API keys or `beta_private/`.
