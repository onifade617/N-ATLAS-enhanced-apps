"""natlas-health: the developer kit for building health applications on N-ATLaS.

    from natlas_health import NatlasClient, HealthAssistant

    client = NatlasClient.from_env()                 # NATLAS_BASE_URL, NATLAS_API_KEY
    client.chat("Sannu!", language="ha").text        # raw N-ATLaS chat
    client.transcribe("note.ogg", language="yo")     # per-language ASR
    client.speak("Ẹ kú àárọ̀", language="yo")         # MMS-TTS voices

    HealthAssistant(client).answer(question, language, facts, guidance)   # grounded + safety layer

Also: natlas_health.evaluate (health eval suite), natlas_health.dataset (fine-tuning data),
natlas_health.playground (browser playground), natlas_health.testing (MockClient, FakeGateway).
"""

__version__ = "0.1.0"

from .assistant import Answer, HealthAssistant  # noqa: E402
from .client import ChatResponse, HealthStatus, NatlasClient, Speech, Transcription  # noqa: E402
from .errors import (  # noqa: E402
    AuthenticationError,
    BadRequestError,
    FeatureNotEnabledError,
    InvalidResponseError,
    NatlasError,
    NotConfiguredError,
    UnavailableError,
)
from .languages import LANGUAGES  # noqa: E402
from .prompts import build_messages  # noqa: E402
from .safety import detect_danger, emergency_notice  # noqa: E402

__all__ = [
    "Answer", "AuthenticationError", "BadRequestError", "ChatResponse", "FeatureNotEnabledError", "HealthAssistant",
    "HealthStatus", "InvalidResponseError", "LANGUAGES", "NatlasClient", "NatlasError", "NotConfiguredError", "Speech",
    "Transcription", "UnavailableError", "build_messages", "detect_danger", "emergency_notice",
]
