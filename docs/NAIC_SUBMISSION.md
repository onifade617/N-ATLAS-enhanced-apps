# NAIC 2026 — Lafiya AI submission guide (Problem Statement 02: Voice-First Access)

**Deadline: 12 October 2026, 11:59 PM WAT. Late submissions are not accepted.**
Use case: primary health information for Nigerians who don't type, via WhatsApp voice notes.

## Requirement checklist

| NAIC requirement | Lafiya evidence | Status |
|---|---|---|
| Voice-driven service for people who don't type | WhatsApp voice-note channel (`navigator/whatsapp.py`) + web mic | ✅ built |
| Voice input uses the **official N-ATLAS ASR** for the language | Gateway `/v1/audio/transcriptions` with NCAIR Hausa/Igbo/Yoruba/Nig.-English models; `LAFIYA_CHALLENGE_MODE=1` disables the browser fallback | ✅ built — needs live gateway |
| Genuine N-ATLAS integration (no other foundation model) | All replies and alerts from `NCAIR1/N-ATLaS`; no other LLM anywhere in the code | ✅ built — needs live gateway |
| **≥50 documented real user interactions** | `/gov/` validation panel, `python manage.py export_evidence` | ❌ to collect (protocol below) |
| 1. Working artefact | Repository + deployed app + live WhatsApp number | ⚠️ deploy |
| 2. N-ATLAS integration evidence | `docs/ARCHITECTURE.md` integration table; evidence CSV columns `asr_engine=n-atlas`, `reply_generated_by=n-atlas`; `natlas_check` output | ⚠️ capture after deploy |
| 3. Real-world validation evidence | Evidence CSV + summary + tester feedback | ❌ to collect |
| 4. Technical documentation | `README.md`, `docs/ARCHITECTURE.md` | ✅ |
| 5. 3–5 minute video | Script below | ❌ to record |
| 6. Team profile | — | ❌ team to write |
| 7. Endorsement / registration | Track B: CAC certificate or IDs | ❌ team to provide |

**Confirm with the Secretariat (naic@nitda.gov.ng) early:** (a) eligibility of team members employed by N-ATLaS
partner organisations, and (b) that a self-hosted N-ATLAS-Kit gateway running the NCAIR ASR models satisfies "official
N-ATLAS ASR service".

## Go-live (about 2 hours once accounts exist)

1. **Gateway** — `bash scripts/deploy_natlas_gateway.sh`, then `python manage.py natlas_check` (see README).
2. **Public URL for this server** — `cloudflared tunnel --url http://localhost:8000` (or `ngrok http 8000`).
   Keep it running for the validation period, or deploy Lafiya to a small VM / Render / Railway.
3. **Twilio WhatsApp sandbox** — Twilio console → Messaging → *Try it out* → *Send a WhatsApp message*.
   Set *When a message comes in* to `https://<public-url>/whatsapp/twilio/` (POST).
4. **`.env`**
   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
   PUBLIC_BASE_URL=https://<public-url>
   LAFIYA_CHALLENGE_MODE=1
   ```
   Restart `python manage.py runserver`.
5. **Smoke test** — from your phone send the sandbox `join <code>`, then `hi`, choose a language, `YES`, your LGA,
   and a voice note. Check `/gov/` → the validation counter shows 1.

Sandbox limits: each tester must first send `join <your-code>` to the sandbox number, and sandbox membership lapses
after about 3 days (re-send the join message). For production, register a WhatsApp Business sender in Twilio.

## Validation protocol (≥50 real interactions)

- **Who:** 15–20 adults across at least three languages (e.g. 6 Hausa, 6 Yoruba, 4 Igbo, 4 Pidgin) — ideally mothers,
  caregivers and community health workers. Aim for ~3 questions each → 50–60 interactions with margin.
- **Consent:** WhatsApp onboarding records consent; also read the one-line purpose statement when recruiting.
- **Tasks** (ask testers to use **voice notes** for at least two):
  1. "Which vaccine does my baby need next?" (or about their own child)
  2. "Where is the nearest clinic?" / "Is malaria risk high this week?"
  3. One free question about pregnancy, blood pressure, diabetes or nutrition.
- **Feedback:** after the session, a 3-question form (understood the answer? would you act on it? would you use it
  again?) — attach results to the submission.
- **Evidence:** `python manage.py export_evidence -o lafiya-evidence.csv` (anonymised) and a screenshot of the `/gov/`
  validation panel. Use `--with-text` only for your own review, and redact names/phone numbers before sharing.

## Video outline (3–5 minutes)

1. **0:00 Problem (30 s)** — maternal deaths, zero-dose children, malaria; information doesn't reach families in their
   language.
2. **0:30 Live WhatsApp demo (2 min)** — a mother sends a **Yoruba voice note**: "Which vaccine does my 6-week-old need
   next?" → transcript echoed (N-ATLaS ASR) → answer in Yoruba (N-ATLaS) with the next vaccines, nearest open clinic and
   a booked reminder, plus a malaria warning for her LGA. Repeat briefly in Hausa. Show a danger-sign message → instant
   emergency referral.
3. **2:30 Intelligence Loop (45 s)** — government dashboard: run the loop, LGA risk map, a personalised alert arriving on
   WhatsApp.
4. **3:15 Integration & validation (45 s)** — architecture diagram, `natlas_check`, validation panel (N real
   interactions, % voice via N-ATLaS ASR, replies by N-ATLaS).
5. **4:00 Impact & ask (30 s)** — pilot with two State Primary Health Care Development Agencies.
