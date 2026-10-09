# natlas-health: the N-ATLaS developer kit for health apps, with Lafiya AI as its reference app

This repository is **developer infrastructure for [N-ATLaS](https://huggingface.co/NCAIR1/N-ATLaS)**. It helps
developers integrate, test, evaluate, adapt and deploy N-ATLaS in health applications for English, Hausa, Yoruba,
Igbo and Nigerian Pidgin. Every part calls the N-ATLaS gateway (chat, ASR, TTS) directly and wraps no other model.

| Developer tool | Command / module | Docs |
|---|---|---|
| **Python SDK**: client, typed errors, cold-start retries, language mapping. Standard library only. | `from natlas_health import NatlasClient` | [docs/sdk](docs/sdk/README.md) |
| **Health safety layer**: grounded prompts, multilingual danger signs, emergency notice, fallback | `HealthAssistant` | [docs/sdk](docs/sdk/README.md#safe-grounded-health-answers) |
| **Browser playground**: chat, grounded answers, mic → ASR, voices, request inspector, code export | `natlas-health playground` | [docs/sdk](docs/sdk/README.md#playground) |
| **Evaluation tools**: 20-case 5-language health suite with safety, grounding, language and format checks | `natlas-health eval` | [docs/sdk](docs/sdk/README.md#evaluate) |
| **Fine-tuning starter kit**: dataset build/validate/split, LoRA/QLoRA script, 200-example seed set | `natlas-health dataset`, `finetune/` | [finetune/README.md](finetune/README.md) |
| **Testing tools**: offline `MockClient`, local `FakeGateway` (no GPU credit spent in CI) | `natlas_health.testing` | [docs/sdk](docs/sdk/README.md#test-without-a-gpu) |
| **Bilingual developer docs** with working examples | English · Naijá (Pidgin) | [EN](docs/sdk/README.md) · [PCM](docs/sdk/README.pcm.md) |
| **Evidence and beta programme**: live-gateway run, per-tester usage from gateway logs | `docs/evidence/`, `scripts/beta/` | [evidence](docs/evidence/README.md) · [beta](docs/beta/README.md) |

Licence: Apache-2.0 for the code ([LICENSE](LICENSE)); models and datasets keep their own terms ([NOTICE](NOTICE)) · Contributing: [CONTRIBUTING.md](CONTRIBUTING.md) · Changes: [CHANGELOG.md](CHANGELOG.md)

```bash
pip install -e .
natlas-health playground --mock                     # try it now, no GPU
NATLAS_BASE_URL=... NATLAS_API_KEY=... natlas-health eval --report report.md
python examples/quickstart.py --mock
```

## Reference app: Lafiya AI

Lafiya is a multilingual, voice-first community health platform (Django) **built on natlas-health**. It shows the
kit in production use. Its whole N-ATLaS integration is [`navigator/natlas.py`](navigator/natlas.py), about 80 lines
on top of the SDK, and its tests run against the SDK's `FakeGateway`. It implements the MVP scope from the
concept brief (`Lafiya_AI_Pitch.pdf`):

| MVP item | Where |
|---|---|
| **Care Navigator** voice assistant (Hausa, Yoruba, Igbo, Pidgin, English) with symptom-to-service referral | `navigator/` · `/navigator/` |
| **MamaCare** pregnancy tracker, WHO 8-contact ANC schedule, danger signs, child milestones to age 5 | `mamacare/` · `/mamacare/` |
| **ImmuniTrack** personal vaccine schedule, reminders, coverage-gap / zero-dose mapping | `immunitrack/` · `/immunitrack/` |
| **ClimateGuard** live weather → malaria, heat and flood risk per LGA, with transparent thresholds | `climateguard/` · `/climate/` |
| **Personalised alerts**: the Intelligence Loop (Sense → Match → Speak → Act → See) | `alerts/engine.py` · `/alerts/` |
| **Facility finder**: nearest open facility by service | `core/geo.py` · `/facilities/` |
| **Government dashboard**: LGA map, coverage gaps, climate risk, impact metrics, CSV export, open API | `dashboard/` · `/gov/`, `/api/v1/` |
| Health-worker view: due/overdue lists, high-risk weeks, referrals, household enrolment | `/worker/` |
| **WhatsApp voice notes**: onboarding, N-ATLaS speech-to-text, answers, alert push | `navigator/whatsapp.py` · `/whatsapp/twilio/` |
| Real-world validation evidence | `dashboard/evidence.py` · `/gov/`, `export_evidence` |

## Quick start

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_lafiya          # loads all 37 states + 774 LGAs; add --offline for simulated weather
python manage.py runserver
```

Open http://127.0.0.1:8000. All demo accounts use the password `lafiya123`:

| User | Role | Scenario |
|---|---|---|
| `funke` | Family (Yoruba, Ibadan North) | Pitch scenario: a mother asks which vaccine her ~6-week-old needs next |
| `amina` | Family (Hausa, Kano Municipal) | 25 weeks pregnant, hypertension, toddler missing measles doses |
| `chinedu` | Family (Igbo, Enugu North) | Diabetes, infant with overdue vaccines |
| `chw` | Health worker, Ibadan North PHC | Due/overdue lists, record vaccines/ANC, complete referrals |
| `gov` | Government partner + Django admin | Live dashboard, export, open API, run the loop |

Run the tests (Lafiya + SDK, no GPU needed): `python manage.py test tests`

## Daily job

Schedule this once a day (cron / Windows Task Scheduler):

```bash
python manage.py run_intelligence_loop     # --offline, --no-natlas, --max-natlas N, --date YYYY-MM-DD
```

It fetches 21 days of history plus a 7-day forecast per LGA from Open-Meteo, scores risk for today and the same day last
week (so trends are real), matches risk to the people it affects (pregnant women, under-5 caregivers, people with
hypertension/diabetes), writes each alert in the person's language, attaches the nearest suitable facility, and
queues vaccine/ANC reminders. Alerts are de-duplicated, so re-running is safe. `update_climate` refreshes risk only.

## Connecting N-ATLaS (N-ATLAS-Kit gateway)

Lafiya talks to the [N-ATLAS-Kit gateway](https://natlas-docs.vercel.app/gateway), which serves the N-ATLaS chat model
**and** per-language speech-to-text (Hausa, Igbo, Yoruba, Nigerian-accented English). Full instructions:
https://natlas-docs.vercel.app/self-hosting. Summary for Modal (needs a 24 GB GPU — A10 or L4):

1. On Hugging Face, accept the terms of all five gated repos — `NCAIR1/N-ATLaS`, `NCAIR1/Hausa-ASR`,
   `NCAIR1/Igbo-ASR`, `NCAIR1/Yoruba-ASR`, `NCAIR1/NigerianAccentedEnglish` — and create a read token.
2. Deploy the gateway from the kit repo (`git clone https://github.com/Kambah123/N-ATLAS-Kit`):
   ```bash
   pip install "modal>=1.0" && modal setup
   modal secret create natlas-hf HF_TOKEN=hf_xxxxxxxx
   modal secret create natlas-api NATLAS_API_KEYS="$(openssl rand -hex 32)"   # keep this key
   modal run serve/modal_preflight.py      # checks token, model terms and GPU access
   modal deploy serve/modal_app.py         # prints https://<workspace>--natlas-serve-natlasservice-serve.modal.run
   ```
   (With a local 24 GB NVIDIA GPU you can instead run `docker compose up --build` in `serve/` → `http://localhost:8080`.)
3. Point Lafiya at it in `.env` and test:
   ```bash
   NATLAS_BASE_URL=https://<workspace>--natlas-serve-natlasservice-serve.modal.run
   NATLAS_API_KEY=<one of your NATLAS_API_KEYS>

   python manage.py natlas_check                                  # health + chat
   python manage.py natlas_check --audio note.ogg --language yo   # + speech-to-text
   ```

What changes once connected:
- **Care Navigator replies and alerts** are written by N-ATLaS in the user's language, grounded in facts from the
  person's own records and WHO/NPHCDA guidance (`navigator/natlas.py`, `navigator/knowledge.py`).
- **Voice input** is recorded in the browser and transcribed by the gateway's ASR models (`/navigator/api/transcribe/`).
  Pidgin uses the Nigerian-accented English model. Spoken replies still use browser speech synthesis (the gateway has
  no text-to-speech).
- The Modal deployment scales to zero after 5 idle minutes; the first request after that is a cold start. Lafiya
  never waits on it: timeouts fall back to templates / browser speech. Run `natlas_check` before a live demo to warm it.

Safety logic never depends on the model: danger-sign detection always adds the emergency referral and "call 112".
Any other OpenAI-compatible N-ATLaS server (e.g. `vllm serve NCAIR1/N-ATLaS --max-model-len 8192`) also works for chat.

**Licence:** N-ATLaS is free for organisations with up to 1,000 monthly active users; larger deployments (e.g. a
two-state pilot) need a commercial licence from Awarri. Attribution ("Powered by N-ATLaS (Awarri)") is shown in the footer.

## WhatsApp voice-note channel

Families can use Lafiya entirely by WhatsApp voice note. First contact runs onboarding (language → consent → LGA or
shared location); after that every voice note is transcribed by N-ATLaS ASR and answered in the person's language with
the nearest facility and any booked reminder. STOP deletes all their data; LANGUAGE changes language. Households
enrolled by a health worker are recognised by phone number. New personalised alerts are pushed on WhatsApp to people
with an active session. Setup (Twilio sandbox + tunnel): see [docs/NAIC_SUBMISSION.md](docs/NAIC_SUBMISSION.md#go-live-about-2-hours-once-accounts-exist).

## NAIC 2026 submission

This branch targets **Problem Statement 01, Developer Infrastructure**. See [docs/NAIC_PS01.md](docs/NAIC_PS01.md).
The earlier Voice-First Access (PS02) plan is kept in [docs/NAIC_SUBMISSION.md](docs/NAIC_SUBMISSION.md), with its
requirement checklist, validation protocol and video outline, and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the
architecture and N-ATLaS integration points. `python manage.py export_evidence` exports the anonymised log of real
interactions (demo data excluded); set `LAFIYA_CHALLENGE_MODE=1` so voice input only uses N-ATLaS ASR.

## Geography: all 36 states + FCT and 774 LGAs

Registration, profiles, ClimateGuard and the government map cover every state and LGA in Nigeria
(`core/data/nigeria_lgas.csv`, loaded by `python manage.py load_geography` — safe to re-run, also run by
`seed_lafiya`). Each LGA has its official P-code and centre point, which drive live weather and risk for all 774 LGAs.
A full national weather refresh takes 1–2 minutes because Open-Meteo's free tier allows ~600 locations per minute;
Lafiya batches 50 LGAs per request and waits out the limit automatically.

Source: Nigeria Subnational Administrative Boundaries (COD-AB v01) — Office of the Surveyor General of the Federation
(OSGOF), eHealth Africa and UN Cartographic Section, published by OCHA on HDX
(https://data.humdata.org/dataset/cod-ab-nga), licensed CC BY-IGO 3.0. A few spellings are corrected in
`core/geography.py` (e.g. Obio/Akpor, Port Harcourt, Omuma, Garun Mallam, Atisbo).

## Health facilities: ~55,000 real facilities in all 774 LGAs

The facility finder, Care Navigator, alerts and WhatsApp replies use **54,782 real health facilities**
(`core/data/nigeria_health_facilities.csv.gz`, loaded by `python manage.py load_facilities` — also run by
`seed_lafiya`; safe to re-run, and it re-points anything that referenced the old demo facilities):

- **GRID3 Nigeria Health Facilities v3.0** (24 states, 2025) and **v2.0** (the other 13 states), built from the
  **Nigeria Health Facility Registry** (2024/2026), NPHCDA and field surveys — CC BY 4.0, via HDX
  ([v3.0](https://data.humdata.org/dataset/grid3-nga-health-facilities-v3-0),
  [v2.0](https://data.humdata.org/dataset/grid3-nga-health-facilities-v2-0)). Rebuild with
  `python scripts/build_facilities_csv.py <v3.gpkg> <v2.gpkg>`.
- Kept: name, type, level, public/private ownership, registry code, coordinates. Dropped: closed/not-functional sites
  and records without coordinates. Each facility is matched to one of the 774 LGAs (99.9% by name, the rest by the
  nearest LGA in its state).
- **Not in the data: opening hours, phone numbers and service lists.** Lafiya infers *likely* services from the
  facility type (e.g. public PHCs → immunization, ANC, delivery, malaria) and *typical* hours (PHCs Mon–Fri 08:00–16:00,
  hospitals 24 h), marks them unverified, and says so to users ("usually open at this time — hours not confirmed").
- Restricted-access sites (staff clinics, barracks, police, prisons, NYSC camps, school clinics) are never used for
  service referrals.
- Synthetic demo families still live only in 27 LGAs across 7 states; `seed_lafiya --demo-facilities` uses the old
  81 synthetic facilities instead of the real ones.

## Deploying on Render

The Django app runs on Render; **N-ATLaS stays on the Modal gateway** (Render has no GPUs, and the
gated model weights must never be committed to Git).

1. Push this repository to GitHub (`.env`, `db.sqlite3` and model files are git-ignored).
2. Render dashboard → **New → Blueprint** → select the repo. `render.yaml` creates a PostgreSQL database and the
   web service; `build.sh` runs migrations and loads all 774 LGAs, ~55,000 facilities and (first deploy only) the
   demo accounts, then fetches live weather — the first build takes several minutes.
3. When prompted, enter the secret values from your local `.env`: `NATLAS_BASE_URL`, `NATLAS_API_KEY`
   (and `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` once WhatsApp is set up — leave them blank until then).
4. For WhatsApp, set the Twilio sandbox webhook to `https://<your-app>.onrender.com/whatsapp/twilio/`.
   `PUBLIC_BASE_URL` defaults to the Render URL.

Plans: the blueprint uses Render's **free** web service and Postgres. Free web services sleep after 15 minutes idle
(first request then takes ~1 minute) and free Postgres expires after 30 days — switch the web service to
`starter` before WhatsApp testers use it. The daily Intelligence Loop cron job is included but commented out
(Render cron jobs are paid); the government dashboard's "Run Intelligence Loop" button works meanwhile.

Modal credit: only N-ATLaS questions (chat, voice, WhatsApp) wake the GPU — page views and Render health checks do not.
`LAFIYA_NATLAS_FOR_ALERTS=0` keeps daily alerts on templates.

## Design notes

- **Medical safety** — Lafiya educates and refers; it never diagnoses. Danger signs trigger emergency referral first.
- **Explainable risk** — scoring thresholds are in `climateguard/risk.py`, published on `/climate/`, and every alert
  stores a plain-language "why".
- **Data protection (NDPA 2023)** — consent is required at signup/enrolment; users can download (`/profile/export/`) or
  delete their data; dashboards are aggregated; the CSV export and open API suppress counts below `ANON_MIN_CELL`.
- **Voice** — with the gateway connected, speech-to-text uses N-ATLaS ASR models; without it, the browser Web Speech
  API (`static/js/voice.js`), whose Hausa/Yoruba/Igbo support is limited. Text-to-speech is browser-only for now.
- **Zero extra dependencies** — only Django; front-end libraries (Bootstrap, Leaflet, Chart.js) load from CDNs.

## Before a pilot

- Hausa, Yoruba, Igbo and Pidgin fallback strings (`alerts/messages.py`, `navigator/phrases.py`) are draft translations
  and need native-speaker review.
- Facilities, households and phone numbers in the seed are **synthetic**; load real facility lists (e.g. the Nigeria
  Health Facility Registry) and validate the vaccine schedule against current NPHCDA/State guidance (editable in admin).
- Replace SQLite with PostgreSQL and set `DJANGO_DEBUG=0`, `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS`.
- Roadmap items from the brief (SMS delivery, USSD/IVR, DHIS2 integration, more disease models) are out of MVP scope.
