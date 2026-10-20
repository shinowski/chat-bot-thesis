"""Warning-sign routing, not diagnosis or validated triage.

Source: https://www.aad.org/public/everyday-care/itchy-skin/rash/rash-101
These rules and their urgency wording still require clinician review.
"""

import re

from model.text_understanding import normalize_message, negation_prefix


SAFETY_RESPONSES = {
    "emergency": (
        "Please seek emergency medical care now. Call your local emergency number "
        "or go to the nearest emergency department. Do not wait for a photo result."
    ),
    "medical_attention": (
        "Some symptoms you've described need an in-person medical assessment. "
        "Please seek medical care promptly; a skin photo or chat cannot rule out a serious problem. "
        "If you have trouble breathing or swallowing, or swelling of the eyes, lips, mouth, "
        "or throat, seek emergency care immediately."
    ),
    "safety_information": (
        "Trouble breathing or swallowing, or swelling of the eyes, lips, mouth, or throat, "
        "can need emergency medical care. If this is happening now, seek emergency care immediately. "
        "A skin photo cannot assess these symptoms."
    ),
    "safety_check": (
        "Could you describe what is happening? Are you having trouble breathing or swallowing, "
        "or swelling of your eyes, lips, mouth, or throat right now? If yes, seek emergency "
        "medical care immediately. Otherwise, tell me the symptoms you're concerned about "
        "so I can respond more appropriately."
    ),
}

GENERAL_CARE_GUIDANCE = (
    "See a doctor or dermatologist if you're concerned about a rash or need a diagnosis and treatment. "
    "Seek medical care promptly if a rash covers most of your body, spreads rapidly, is painful, "
    "blisters or forms open sores, comes with fever or illness, involves the eyes, lips, mouth, "
    "or genital skin, or has pus or yellow crusts. "
    "If you have trouble breathing or swallowing, or swelling of the eyes or lips, "
    "seek emergency care immediately. "
    "These are signs to watch for; your question alone does not mean you are having an emergency."
)


def is_care_question(message):
    """Recognize requests about seeking care, rather than reports of danger."""
    text = normalize_message(message)
    professional = r"(?:doctor|dermatologist|physician|specialist|hospital|clinic|medical (?:care|attention|help))"
    return bool(re.search(r"\b" + professional + r"\b", text)) and bool(re.search(
        r"\b(?:when|should|do i need|do we need|need to|have to|can i|could i|must i|"
        r"is it time|is it necessary|see|consult|visit|seek|go to|get checked)\b", text
    ))

EMERGENCY_PATTERNS = (
    r"(?:cannot|can not|unable to|not able to|barely) (?:breathe|swallow)",
    r"(?:difficulty|trouble|problems?|hard time|hard|struggling) (?:with |to )?(?:breathing|swallowing|breathe|swallow)",
    r"(?:breathing|swallowing)\b[^.;!?]{0,28}\b(?:difficult|hard|trouble)",
    r"short(?:ness)? of breath",
    r"(?:throat|tongue|lips?|eyes?|face|mouth|airway|windpipe)\b[^.;!?]{0,28}\b(?:swelling|swollen|swelled up|getting bigger)",
    r"(?:swelling|swollen|swelled up)\b[^.;!?]{0,28}\b(?:throat|tongue|lips?|eyes?|face|mouth|airway|windpipe)",
    r"chest (?:feels|is) tight",
)
SKIN_PATTERNS = (
    r"blisters?|blistering|open sores?|raw skin",
    r"pus|(?:yellow|golden) crusts?|unpleasant smell",
    r"(?:spreading|spreads) (?:very )?(?:rapidly|quickly|fast)",
    r"(?:rapidly|quickly) spreading",
    r"fever|feverish|painful|unbearable|very ill",
    r"(?:most of|all over) (?:my |the |his |her )?body",
)


def _negated(clause, match):
    # Scope negation locally. "Cannot breathe" and "not able to breathe"
    # are affirmative warning patterns, not negated symptom reports.
    prefix = negation_prefix(clause[:match.start()])
    matched = re.sub(r"^not able to\b", "", match.group())
    return bool(re.search(r"\b(?:no|not|never|without)\b", matched)) or bool(re.search(
        r"\b(?:no|not|never|without|deny|denies)\b(?:\s+\w+){0,6}\s*$", prefix
    )) or bool(re.match(r"\s+(?:is|are)\s+not\b", clause[match.end():]))


def _matches(clauses, patterns):
    found, denied = False, False
    for clause in clauses:
        for pattern in patterns:
            for match in re.finditer(r"\b(?:" + pattern + r")\b", clause):
                if _negated(clause, match):
                    denied = True
                else:
                    found = True
    return found, denied


def safety_intent(message, predicted_intent=None):
    text = normalize_message(message)
    clauses = re.split(
        r"[.;!?\n]+|\b(?:but|however|although|yet)\b|\band\s+(?=(?:my|i|he|she|his|her|their|the)\b)", text
    )
    emergency, denied_emergency = _matches(clauses, EMERGENCY_PATTERNS)
    skin_context = bool(re.search(r"\b(?:rash|skin|hives|lesion|blisters?|blistering)\b", text))
    medical, _ = _matches(clauses, SKIN_PATTERNS)
    mouth_rash = any(
        _matches([clause], (r"eyes?|lips?|mouth|genitals?|genital",))[0]
        and _matches([clause], (r"rash|sores?|peeling|blisters?|blistering",))[0]
        for clause in clauses
    )

    # Personal reports such as "Can you help? My lips are swollen" still win.
    personal = bool(re.search(r"\b(?:my|our|i have|i am|i cannot|he has|she has|child has|baby has)\b", text))
    educational = not personal and bool(re.search(
        r"\b(?:explain|define|what (?:is|are|does)|meaning of|can a|can eczema|can psoriasis|if someone|can(?: \w+){1,3} (?:cause|trigger|lead to))\b", text
    ))
    hypothetical = bool(re.match(r"\s*(?:what (?:should|would) i do |what )?if i (?:get|develop|experience)\b", text))
    if (educational or hypothetical) and (emergency or denied_emergency):
        return "safety_information"
    if emergency:
        return "emergency"
    if not (educational or hypothetical) and skin_context and (medical or mouth_rash):
        return "medical_attention"
    if denied_emergency:
        return "safety_information"
    if re.search(r"\b(?:breathe|breathing|swallow|swallowing) (?:normally|fine|okay|well|easily)\b", text):
        return "safety_information"
    # A learned label is not evidence that a current emergency is happening.
    # Ask about warning signs for unfamiliar wording instead of asserting urgency.
    if predicted_intent == "emergency":
        if is_care_question(message):
            return None
        return "safety_information" if educational or hypothetical else "safety_check"
    return None


def safety_response(intent, conversation, message=None):
    """Available even before the embedding model has loaded."""
    if intent in {"emergency", "medical_attention"}:
        conversation.set("screening_paused", True)
        conversation.set("last_knowledge_topics", [])
        if message:
            conversation.add_symptom(message)
    conversation.set("last_reply_intent", intent)
    if intent != "safety_check":
        conversation.set("pending_question", None)
    return dict(
        reply=SAFETY_RESPONSES[intent], intent=intent, confidence=None,
        confidenceSource=None, modelConfidence=None, predictedIntent=None,
        followUps=[], action=None,
    )
