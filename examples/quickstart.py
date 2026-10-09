"""natlas-health quickstart: every SDK feature in one file.

    python examples/quickstart.py            # uses NATLAS_BASE_URL / NATLAS_API_KEY from the environment or .env
    python examples/quickstart.py --mock     # no GPU needed
"""

import sys

from natlas_health import HealthAssistant, NatlasClient, NatlasError
from natlas_health.cli import load_dotenv
from natlas_health.testing import MockClient

load_dotenv()
client = MockClient() if "--mock" in sys.argv else NatlasClient.from_env(retries=2)

# 1. Is the gateway up? (Modal deployments scale to zero; the first call can take minutes.)
print("health:", client.health(timeout=60))

# 2. Raw chat, with the Hausa chat template.
try:
    print("chat:", client.chat("Sannu! Ka gaishe ni a jumla daya.", language="ha", max_tokens=40).text)
except NatlasError as exc:
    print("chat failed:", exc)

# 3. A grounded health answer with the safety layer.
assistant = HealthAssistant(client, assistant_name="Lafiya")
answer = assistant.answer(
    "Abẹ́rẹ́ àjẹsára wo ni ọmọ mi nílò báyìí?",  # "Which vaccine does my child need now?"
    language="yo",
    facts=["Child: Tobi, 6 weeks old.", "Next vaccines due 14 Oct 2026: Pentavalent 1, OPV 1, PCV 1, Rotavirus 1."],
    guidance=["NPHCDA schedule: at 6 weeks give Pentavalent 1, OPV 1, PCV 1 and Rotavirus 1."],
    fallback="Tobi's next vaccines are Pentavalent 1, OPV 1, PCV 1 and Rotavirus 1, due 14 Oct 2026.",
)
print(f"answer [{answer.generated_by}, emergency={answer.emergency}]:", answer.text)

# 4. Danger signs always get the emergency notice first, whatever the model says.
urgent = assistant.answer("Ina da ciki kuma ina zubar jini", language="ha", facts=["30 weeks pregnant"])
print("urgent:", urgent.text.splitlines()[0])

# 5. Voice: text-to-speech, then speech-to-text on the same clip.
try:
    speech = client.speak("Ẹ kú àárọ̀. Ẹ mú Tobi lọ sí ilé ìwòsàn lónìí.", language="yo")
    with open("hello_yo.wav", "wb") as fh:
        fh.write(speech.audio)
    print("speech: hello_yo.wav, voice", speech.voice)
    print("transcript:", client.transcribe(speech.audio, "hello_yo.wav", "audio/wav", language="yo").text)
except NatlasError as exc:
    print("voice failed:", exc)
