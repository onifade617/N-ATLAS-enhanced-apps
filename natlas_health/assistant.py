"""HealthAssistant: grounded, safe health answers from N-ATLaS in five Nigerian languages.

    from natlas_health import NatlasClient, HealthAssistant

    assistant = HealthAssistant(NatlasClient.from_env())
    answer = assistant.answer(
        "Which vaccine does my baby need next?", language="yo",
        facts=["Child: Tobi, 6 weeks old.", "Next vaccines: Pentavalent 1, OPV 1, PCV 1 - due today."],
        fallback="Tobi's next vaccines are Pentavalent 1, OPV 1 and PCV 1, due today.",
    )
    print(answer.text, answer.generated_by, answer.emergency)

Guarantees, whatever the model does:
  * a detected danger sign always puts the emergency notice (go now / call 112) first;
  * if the gateway is unconfigured, down or cold-starting, you get your ``fallback`` text instead of an exception;
  * markdown is stripped so the reply can go to WhatsApp or text-to-speech.
"""

import logging
from dataclasses import dataclass

from . import prompts, safety, text
from .errors import NatlasError

log = logging.getLogger(__name__)

DANGER_FACT = "DANGER SIGN reported: they must go to the nearest health facility now or call 112."


@dataclass
class Answer:
    text: str
    language: str
    emergency: bool
    generated_by: str  # "n-atlas" or "fallback"
    latency_ms: int = 0
    error: str = ""
    raw: str = ""  # N-ATLaS's reply exactly as received (before markdown stripping and the emergency notice)


class HealthAssistant:
    def __init__(self, client, assistant_name="Lafiya", extra_danger_keywords=(), temperature=0.3, max_tokens=500):
        self.client = client
        self.assistant_name = assistant_name
        self.extra_danger_keywords = tuple(extra_danger_keywords)
        self.temperature = temperature
        self.max_tokens = max_tokens

    def messages(self, question, language, facts, guidance=None, history=None, emergency=False):
        """The exact chat messages sent to N-ATLaS."""
        facts = list(facts or ()) + ([DANGER_FACT] if emergency else [])
        return prompts.build_messages(language, facts, guidance, question=question, history=history,
                                      assistant=self.assistant_name)

    def compose(self, language, facts, guidance=None, question=None, history=None):
        """Model-only: the grounded reply text, or None if N-ATLaS is unavailable. No safety prefix."""
        try:
            return self.generate(language, facts, guidance, question, history).text or None
        except NatlasError as exc:
            log.warning("N-ATLaS chat failed: %s", exc)
            return None

    def answer(self, question, language="en", facts=(), guidance=(), history=None, fallback=None,
               emergency=None, emergency_notice=None):
        """Grounded answer with the safety guarantees above.

        emergency         force the emergency path (True/False); default: detect danger signs in ``question``
        emergency_notice  your own urgent text (e.g. with the nearest facility); default: EMERGENCY_NOTICE
        """
        if emergency is None:
            emergency = safety.detect_danger(question or "", self.extra_danger_keywords)
        notice = emergency_notice or safety.emergency_notice(language)
        try:
            resp = self.generate(language, facts, guidance, question, history, emergency)
            raw = resp.text
            body, generated_by, latency, error = text.plain_text(raw), "n-atlas", resp.latency_ms, ""
        except NatlasError as exc:
            log.warning("N-ATLaS chat failed: %s", exc)
            raw, body, generated_by, latency, error = "", fallback or "", "fallback", 0, str(exc)
        if not body and generated_by == "n-atlas":
            body, generated_by = fallback or "", "fallback"
        if emergency:
            body = notice + ("\n\n" + body if body else "")
        return Answer(text=body, language=language, emergency=emergency, generated_by=generated_by,
                      latency_ms=latency, error=error, raw=raw)

    def generate(self, language, facts, guidance=None, question=None, history=None, emergency=False):
        """Raw model call with the grounded prompt. Returns ChatResponse; raises NatlasError."""
        return self.client.chat(self.messages(question, language, facts, guidance, history, emergency), language=language,
                                temperature=self.temperature, max_tokens=self.max_tokens)
