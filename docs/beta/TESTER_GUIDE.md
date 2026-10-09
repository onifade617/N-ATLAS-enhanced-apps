# Help test natlas-health (about 30 minutes)

natlas-health is a free toolkit that makes it easy to build health apps on N-ATLaS, Nigeria's AI language
model, in English, Hausa, Yoruba, Igbo and Pidgin. Please try it and tell us honestly what was hard.

You need Python 3.9 or newer, plus your **tester ID** and **API key**, which come from me privately. Use
made-up details only. The system never records what you type or say.

## Step 1: install

Open a terminal (on Windows, PowerShell) and run:

```bash
pip install "git+https://github.com/onifade617/N-ATLAS-enhanced-apps"
```

## Step 2: connect with your key

Windows PowerShell:

```powershell
$env:NATLAS_BASE_URL="<URL from my message>"
$env:NATLAS_API_KEY="<your key>"
```

Mac/Linux:

```bash
export NATLAS_BASE_URL="<URL from my message>"
export NATLAS_API_KEY="<your key>"
```

Then:

```bash
natlas-health health --timeout 600
```

The first time can take 2–3 minutes while the AI wakes up. Wait until it says `OK`.

## Step 3: talk to N-ATLaS

Use your language: `ha`, `yo`, `ig`, `pcm` or `en`.

```bash
natlas-health chat "Greet me in one sentence." --language yo
natlas-health ask "Which vaccine does my baby need next?" --language yo --fact "Child: Tobi, 6 weeks old"
natlas-health ask "I am pregnant and I am bleeding" --language yo
```

The last one should start with an emergency message telling the person to go to a hospital or call 112.
Did it?

## Step 4: try the playground

```bash
natlas-health playground
```

Open http://127.0.0.1:8765 in your browser, then:

- pick a sample case and press **Ask N-ATLaS**;
- on the **Voice** tab, record a short question, then press **Speak** to hear a reply.

Press Ctrl+C in the terminal when you're done.

## Step 5: tell me how it went

Fill in the feedback form from my message, using your tester ID. If anything failed, copy the exact error
text into the form.

Thank you!
