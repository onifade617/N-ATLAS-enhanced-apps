# natlas-health beta: step-by-step guide for 30 testers

**Goal:** show the judges that real Nigerian developers installed natlas-health, called N-ATLaS and built
with it, and that we improved the kit from what they told us. For PS01 the beta users are **developers**,
not patients.

**Deadline: Monday 12 Oct 2026, 11:59 PM WAT.** Submit Monday afternoon, not at 11:58 PM.

| Day | Steps |
|---|---|
| Fri 9 Oct | Steps 1–5: set up your PC, list testers, issue keys, create the form, send invites |
| Sat 10 Oct | Steps 6–7: sessions A and B, then export logs |
| Sun 11 Oct | Steps 6–8: session C, fix what broke, export logs |
| Mon 12 Oct | Steps 9–12: reports, docs, video, submit |

---

## Step 1: set up your PC (once, about 15 minutes)

You need Python 3.9 or newer, Git, the Modal CLI (to manage the gateway) and the GitHub CLI (to push).

```bash
cd "C:\Users\HP PC\Documents\GitHub\N-ATLAS enhanced apps"
git pull
pip install -e .                       # natlas-health + the natlas-health command
natlas-health --version                # natlas-health 0.1.0
modal profile current                  # your Modal workspace (onifade617)
python manage.py test tests            # should end with "OK"
```

Your `.env` already holds `NATLAS_BASE_URL` and your own `NATLAS_API_KEY`. Check that the GPU wakes and
answers (this costs a little credit):

```bash
natlas-health health --timeout 600
natlas-health chat "Sannu!" --language ha
```

Check your remaining credit on the Modal dashboard (Billing). The whole beta should cost about $10–15. Over
roughly $25 in total, schedule fewer or shorter sessions.

## Step 2: build the tester list

Make a Google Sheet with two columns, **name** and **contact** (email or phone), one row per person, and
download it as `testers.csv`. Aim for a mix:

- about 10 experienced developers, 10 students and 10 others (data, ML or health-tech);
- at least **2 fluent speakers each of Hausa, Yoruba, Igbo and Pidgin**, who do the language review (task 7);
- as many as possible from **outside Awarri**. Independent testers make stronger evidence.

Split them into **three sessions of about 10**. The gateway serves 8 requests at once per GPU, so 30 people
at once would start extra GPUs and cost more.

| Session | When | Who |
|---|---|---|
| A | Sat 10 Oct, 11:00–12:30 | T01–T10 |
| B | Sat 10 Oct, 16:00–17:30 | T11–T20 |
| C | Sun 11 Oct, 14:00–15:30 | T21–T30, plus anyone who missed A or B |

## Step 3: issue the keys (about 10 minutes)

```bash
python scripts/beta/keys.py import testers.csv     # gives T01…T30 a private key each
python scripts/beta/keys.py list                   # check names and ids
python scripts/beta/keys.py secret                 # prints 2 commands; run them exactly
```

The two printed commands install all 30 keys plus yours on the gateway. Neither starts a GPU.

- If the `natlas-api` secret holds other keys you still use, add them first, because the command replaces the
  whole list.
- Everything lands in `beta_private/`, which is git-ignored. **Never commit it, screenshot it or paste it in a
  group.**

Test one tester key (replace `<T01 key>` with the key from `beta_private/roster.csv`):

```bash
natlas-health chat "hello" --api-key <T01 key>      # works = keys installed
```

## Step 4: create the feedback form (about 20 minutes)

Copy the 31 questions from [FEEDBACK_FORM.md](FEEDBACK_FORM.md) into a Google Form. Keep the consent question
first and the tester-id question required. Set responses to go to a Google Sheet. Copy the form link.

## Step 5: send the invites (about 20 minutes)

```bash
python scripts/beta/keys.py invites --form "<form link>" --session "Sat 10 Oct, 11:00, <Google Meet link>"
```

This writes one message per tester in `beta_private/invites/T01.txt` … `T30.txt`, each containing that
person's own key. **Send each one privately** by email or direct message, never in a group chat. Fix the
session line per person (A, B or C) before sending. Send a reminder the evening before each session.

## Step 6: run each session (90 minutes)

**15 minutes before:**

```bash
natlas-health health --timeout 600       # wakes the GPU so nobody waits through a cold start
```

**During:**

1. Welcome (5 min). Explain that this is a developer test with made-up data, that finding problems is the
   point, and that the gateway logs no prompts or replies.
2. Everyone works through [TESTER_GUIDE.md](TESTER_GUIDE.md), tasks 1–6, at their own pace (60 min). Language
   reviewers also do task 7.
3. You stay on the call and keep a **"stuck log"**: every time someone is stuck, write the time, tester id,
   task, what happened and the exact error. This is your most valuable evidence.
4. Last 10 minutes: everyone fills the form while still on the call. Forms filled "later" mostly never arrive.

**Common problems and fixes:**

| Symptom | Fix |
|---|---|
| `pip` not found / wrong Python | `python -m pip install ...` (Windows: `py -m pip install ...`) |
| `git` not found during install | install Git, or send them the wheel: `python -m pip wheel . --no-deps` |
| `AuthenticationError` | key pasted wrong or not yet installed: check step 3 |
| `UnavailableError` / long wait | GPU cold start: wait 2–3 min and retry; warm it before sessions |
| Yoruba/Igbo letters garbled on Windows | run `chcp 65001` first, or use the playground |
| Microphone not working in playground | use the file upload instead, or Chrome/Edge |

## Step 7: export the logs every night (5 minutes, no GPU cost)

Modal deletes logs after **1 day**. If you skip a night, that evidence is gone.

```bash
mkdir -p beta_private/logs
modal app logs natlas-serve --since 1d --search '"event":"request"' --tail 100000 > beta_private/logs/2026-10-10.jsonl
python scripts/beta/usage.py beta_private/logs/       # quick look: who has made live calls
```

Use the right date in the file name each night (Sat, Sun, and Mon morning). Then send a short nudge to
anyone who still shows zero requests.

## Step 8: fix what broke (Sunday)

Sort the stuck log and the form's question 27 by how many people hit each problem. Fix the top 3–5 before
session C: a doc sentence, an error message or a code fix. Commit each fix with a clear message and note the
commit hash. The beta report's "what we fixed" table is built from these.

## Step 9: build the reports (Monday morning)

1. Final log export (step 7), then the public usage report:
   ```bash
   python scripts/beta/usage.py beta_private/logs/ -o docs/beta/usage_report.md
   ```
2. Download the form responses as CSV and compute the numbers for the report:
   - completion rate per task;
   - median minutes per task;
   - average ratings;
   - the 0–10 "likely to use" score.

   A spreadsheet is enough.
3. Copy [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) to `docs/beta/BETA_REPORT.md` and fill **every** `…`.
   - Quote only people who agreed (form question 31).
   - Name only those who agreed (question 2).
   - Never include contacts or keys.
4. Apply the language corrections from task 7, and say so in the report.

## Step 10: update the submission documents

| Document | Update |
|---|---|
| `docs/NAIC_PS01.md` | Tick the beta row and link `beta/BETA_REPORT.md`. Update any numbers that changed. |
| `README.md` | Add one line to **Proof**: "Beta: N developers, X% made a live call, median Y minutes" with a link. |
| `CHANGELOG.md` | Add a `0.1.1` entry listing the fixes from the beta. |
| `docs/evidence/` | Only re-run `natlas-health eval` if prompts or checks changed; otherwise keep the 9 Oct run. |

Then commit and push, and tag the version you submit, so judges see exactly what you submitted:

```bash
git add -A && git commit -m "Beta report and fixes from 30-developer beta"
git tag -a v0.1.1 -m "NAIC 2026 PS01 submission" && git push && git push --tags
```

## Step 11: record the video (3–5 minutes)

Follow the outline in [NAIC_PS01.md](../NAIC_PS01.md#video-outline-35-min) and add one slide of beta
results. Warm the GPU first so the demo doesn't sit through a cold start.

## Step 12: submit

Check every row of the checklist in `docs/NAIC_PS01.md`:

- [ ] repository link;
- [ ] video;
- [ ] team profile;
- [ ] registration documents;
- [ ] eligibility confirmed with naic@nitda.gov.ng: switching from PS02 to PS01, and staff of N-ATLaS partner
  organisations being allowed to enter.

**Submit by Monday afternoon.**

After submitting, keep the beta running. Revoke keys of people who have finished
(`python scripts/beta/keys.py revoke T05`, then `secret`), and keep exporting logs. You can show more
evidence at the shortlist (16–20 Oct) and the finals (8–10 Nov).

---

### Privacy and safety rules (tell every tester)

- Made-up health data only. This is a developer test, not medical advice.
- The gateway logs feature, language, timing and a key fingerprint, never prompts, replies, audio or keys.
- Each person's key is private. Revoke any key that is shared.
- Use form answers only as consented: anonymised by default, named only with a "yes".
