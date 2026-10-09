# natlas-health beta programme (organiser's playbook)

**Goal:** show the judges that real Nigerian developers can install natlas-health, call N-ATLaS and build
health features with it, and that we improved the kit from what they told us.

**For PS01, the beta users are developers, not patients.** The deliverable is a developer kit, so the people
to recruit are developers. The evidence that counts is: they got it working, how long that took, what they
built, and what broke. Testing Lafiya with families is a separate exercise (PS02); it is not needed here.

## Timeline (deadline Monday 12 Oct, 11:59 PM WAT)

| When | What |
|---|---|
| **Fri 9 Oct** (today) | Decide repo access (step 1). Invite 10–15 developers and expect 6–10 to finish. Create the feedback form. |
| **Sat 10 Oct** | Issue keys and send the tester guide in the morning. **Live session 1** (90 min, online) in the afternoon. Export logs at night. |
| **Sun 11 Oct** | **Live session 2** for those who missed Saturday. Fix the top 3 problems testers hit. Export logs at night. |
| **Mon 12 Oct** | Morning: final log export, usage report, beta report, record the video. Submit by the evening, not at 11:58 PM. |
| 13 Oct onwards | Keep the beta running. Shortlisting is 16–20 Oct and the finals 8–10 Nov, so evidence keeps growing. |

Live group sessions share one warm GPU. Ten people calling at once costs about the same as one person, and
nobody waits through a cold start. Scattered solo testing wakes the GPU again and again.

## Step 1: give testers access to the code

The repository is **private**. Choose one:

- **Make it public (recommended).** It is meant to be open tooling, and the judges must see it anyway. Before
  you do, add a `LICENSE` file. The repo has none yet, and without one "open source" is not true. Check with
  Awarri whether you may publish this under an open licence, since you are an employee.
  Testers then install with:
  `pip install "git+https://github.com/onifade617/N-ATLAS-enhanced-apps"`
- **Keep it private.** Add each tester as a read-only collaborator:
  `gh api -X PUT repos/onifade617/N-ATLAS-enhanced-apps/collaborators/<github-user> -f permission=pull`
  This needs the `onifade617` login. Or send them the wheel from `python -m pip wheel . --no-deps` together with
  a PDF of `docs/sdk/README.md`.

## Step 2: one API key per tester

Per-tester keys give you **per-person usage evidence without collecting anyone's content**. The gateway
logs a fingerprint of the key, never the key, prompt, reply or audio. You can also cut off a single person.

```bash
python scripts/beta/keys.py add "Ada Okafor" "Musa Bello" --contact ada@example.ng --contact +234...
python scripts/beta/keys.py secret        # prints two commands; run them (no GPU is started)
```

- The roster lives in `beta_private/`, which is git-ignored. Never commit it or paste keys in group chats;
  send each person only their own key, privately.
- `secret` rebuilds the gateway's key list from your `.env` key plus every active tester. If the `natlas-api`
  secret holds other keys you still use, add them first, because `--force` replaces the list.
- `python scripts/beta/keys.py revoke "Musa Bello"` then `secret` removes a key.

## Step 3: feedback form

Copy [FEEDBACK_FORM.md](FEEDBACK_FORM.md) into a Google Form. Turn on "collect email" only if you need it. Put
the consent question first. Ask testers to use their tester id (T01…) so form answers match the usage logs.

## Step 4: run the sessions

1. 10 min before: `natlas-health health --timeout 600` to warm the GPU.
2. Share [TESTER_GUIDE.md](TESTER_GUIDE.md). Testers work through tasks 1–6 at their own pace; you stay on the
   call to unblock people and **write down every place someone gets stuck**. That list is your most valuable
   output.
3. Ask people who speak Hausa, Yoruba, Igbo or Pidgin to do task 7, the language review. This is the
   native-speaker review the submission currently lacks.
4. Last 10 min: everyone fills the form.

## Step 5: collect evidence every night

Modal keeps logs for **1 day only** on your plan. Export them each night or they are gone (no GPU is used):

```bash
mkdir -p beta_private/logs
modal app logs natlas-serve --since 1d --search '"event":"request"' --tail 100000 > beta_private/logs/$(date +%F).jsonl
python scripts/beta/usage.py beta_private/logs/ -o docs/beta/usage_report.md
```

The report shows testers only by id, so it is safe to publish. Your own key (evaluations, demos) is listed
separately as `owner` and never counted as beta usage.

## Step 6: write it up

Fill [REPORT_TEMPLATE.md](REPORT_TEMPLATE.md) as `docs/beta/BETA_REPORT.md`, link it from `docs/NAIC_PS01.md`,
and show it in the video. Be concrete and honest: *"7 of 9 developers made a live N-ATLaS call in a median of
11 minutes; the 2 who didn't were blocked by X, which we fixed in commit abc123"* is far more convincing than
*"users loved it"*.

## Recruiting

- **Where:** your own network, Python Nigeria, GDG and Google Developer Student Club chapters, Data Science
  Nigeria, AI Saturdays Lagos, university CS departments, and health-tech developers.
- **Mix:** a few experienced backend developers, a few students, at least one health-tech person, and at
  least one fluent speaker each of Hausa, Yoruba, Igbo and Pidgin.
- **Independence:** testers from outside Awarri make stronger evidence, given the partner-organisation
  question.
- **Ask:** "90 minutes on Saturday or Sunday to try a new open N-ATLaS developer kit for health apps; you'll
  be credited as a beta tester (with your permission)."

## Budget and safety

- **Credit:** about $1/hour of warm A10 GPU, out of $30/month. Two 90-minute sessions plus scattered use cost
  roughly $5–10. Check the Modal dashboard each evening.
- **Synthetic data only:** testers use made-up children and pregnancies. No real patient data, ever. Tell them
  this is a developer test, not medical advice.
- **Consent:** the form asks for consent to use their anonymised answers, and separately whether you may
  name them.
