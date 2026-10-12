# natlas-health beta report

## Summary

Between 9 and 12 October 2026, **3 Nigerian developers** tested natlas-health against the live N-ATLaS gateway.
**All 3 of 3** returned the feedback form and reported completing all four steps of the
[tester guide](TESTER_GUIDE.md), each reaching a first live N-ATLaS answer in **about 2 minutes**. All three
rated ease of setup, guide clarity, replies in their language and voice features **5 out of 5**, and all three
saw the emergency message on the danger-sign question.

The gateway logs confirm part of this independently: **T02 made 2 Hausa chat calls on 11 October, both
successful** ([usage_report.md](usage_report.md)). The rest of the testing cannot be checked against the logs,
because no logs were saved for 9 October 14:35 UTC to 11 October 10:13 UTC (see Limitations). No fixes were
made as a result of the beta before submission.

## Method

- **Recruitment:** through the team's network. All three testers have 5+ years' development experience.
- **Format:** self-paced testing over three days, following [TESTER_GUIDE.md](TESTER_GUIDE.md): install,
  connect, chat (including a grounded answer and an emergency question), and the playground with voice.
- **Evidence:**
  - gateway request logs, which record feature, language, status and latency per request, never the prompt,
    reply, audio or key. Each tester had their own key;
  - the 13-question feedback form ([FEEDBACK_FORM.md](FEEDBACK_FORM.md)).
- **Data:** synthetic health data only. All three testers consented to anonymised reporting, to being named,
  and to being quoted.

## Participants

| | Count |
|---|---|
| Invited / started / returned feedback | 3 / 3 / 3 |
| Experience 5+ years | 3 |
| Fluent in Hausa · Yoruba · Igbo · Pidgin · English | 2 · 1 · 1 · 2 · 2 |

Testers (named with permission): Ibrahim Aina (T01), Ja'far Musa (T02), Mariam Sadeq (T03).

## Results

From the feedback form:

| Step | Reported working | Minutes to first live answer |
|---|---|---|
| 1 Install | 3 of 3 | |
| 2 Connect (first live N-ATLaS response) | 3 of 3 | 2, 2, 2 |
| 3 Chat, grounded answer, emergency question | 3 of 3 | |
| 4 Playground (sample case, voice) | 3 of 3 | |

Emergency message shown for the danger-sign question: 3 of 3 testers.

| Rating (1–5 unless stated) | Mean | n |
|---|---|---|
| Ease of getting started | 5.0 | 3 |
| Clarity of the guide | 5.0 | 3 |
| Quality of replies in testers' languages | 5.0 | 3 |
| Voice features | 5.0 | 3 |
| Likely to use in a real project (0–10) | 9.3 (8, 10, 10) | 3 |

**Usage (gateway logs, from 9 October 12:31 UTC):** 2 requests, both Hausa chat, by T02 on 11 October,
100% success, median latency 6.5 s. See [usage_report.md](usage_report.md). Requests made with the project's own
key are reported there separately as `owner` and are not counted as beta usage.

## What testers said

No tester reported getting stuck ("None", "Not available", "Not available").

> "The setup is easy, and the communication flow aligns. The improvement should be on the interface."
> (Ja'far Musa, T02)

> "Sample health questions. Improvement should be on the interface." (Mariam Sadeq, T03)

Two of three asked for a better interface. No language errors were reported.

## What we learned and fixed

| Feedback | How many | Action |
|---|---|---|
| Improve the interface | 2 of 3 | Noted for after submission; no change made yet |

## Limitations

- **The logs do not cover the whole beta.** Modal keeps gateway logs for one day on the Starter plan. Saved
  exports cover 8 October 16:09 to 9 October 14:35 UTC, and 11 October 10:13 to 12 October 15:51 UTC. Testing
  between those windows (including all of 10 October) left no record. Most of what testers reported therefore
  rests on the feedback form alone.
- **The logs confirm less than the form reports.** T03 returned the form on 12 October but made no logged calls
  from 11 October 10:13 UTC onward. No tester made a logged speech-to-text or text-to-speech call, although all
  three rated the voice features. Their testing may have fallen in the unlogged window.
- A small sample of three, recruited through the team's network. All ratings are the maximum, which suggests
  a friendly sample rather than a measured result.
- Ratings are self-reported. N-ATLaS reply quality was rated by testers, not by clinicians.
- Only one Yoruba speaker and one Igbo speaker took part, so replies in those languages had a single reviewer.
