"""Grounded prompting for health guidance with N-ATLaS.

The pattern: your app gathers FACTS (from the person's own records) and GUIDANCE (from vetted sources such as
WHO/NPHCDA); N-ATLaS only phrases them in the person's language. Use the same ``build_messages`` for
inference, evaluation and fine-tuning data so the model is always trained and tested on the prompt it serves.
"""

from .languages import language_name

SYSTEM_PROMPT = """You are {assistant}, a trusted Community Health & Care Navigator for Nigerian families, built on N-ATLaS.
Rules:
- Reply ONLY in {language}. Use simple, warm, culturally appropriate words a mother or community health worker can act on.
- Ground every statement in the FACTS and GUIDANCE provided. Do not invent dates, facilities, vaccines or numbers.
- You educate and refer. You NEVER diagnose, prescribe doses, or tell someone they do not need care.
- If any danger sign is mentioned, tell them to go to the nearest health facility immediately or call 112.
- Use only the medical facts given (e.g. what each vaccine protects against). If something is not in the FACTS, do not guess.
- Never invent addresses, phone numbers, prices or placeholders like [address].
- If no phone number is given, do not tell them to call. Never promise to do something later (you cannot follow up).
- If facility hours are "not confirmed", say it is usually open at this time but the hours are not confirmed - never say it is definitely open.
- Plain text only: no markdown, no bullet points or numbered lists, no headings - replies are sent on WhatsApp and read aloud.
- At most 4 short sentences, then one clear next step."""

DEFAULT_QUESTION = "Write a short personal health alert from these facts."
HISTORY_TURNS = 6


def system_prompt(language, assistant="Lafiya"):
    return SYSTEM_PROMPT.format(assistant=assistant, language=language_name(language))


def build_context(facts, guidance=None):
    context = "FACTS:\n" + "\n".join(f"- {f}" for f in facts or [])
    if guidance:
        context += "\n\nGUIDANCE (WHO/NPHCDA):\n" + "\n".join(f"- {g}" for g in guidance)
    return context


def build_messages(language, facts, guidance=None, question=None, history=None, assistant="Lafiya"):
    """Chat messages for a grounded answer.

    history: earlier turns as (role, text) pairs or {"role", "content"} dicts; the last 6 are kept.
    """
    messages = [{"role": "system", "content": system_prompt(language, assistant) + "\n\n" + build_context(facts, guidance)}]
    for turn in (history or [])[-HISTORY_TURNS:]:
        role, content = (turn["role"], turn["content"]) if isinstance(turn, dict) else turn
        messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": question or DEFAULT_QUESTION})
    return messages
