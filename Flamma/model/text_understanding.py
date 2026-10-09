"""Conservative text cleanup shared by the classifier and conversation rules.

Only known aliases are corrected. Original messages remain in conversation
memory; unlisted words, medicine names, numbers, and negation are retained.
"""

import json
from pathlib import Path
import re
import unicodedata

with (Path(__file__).resolve().parents[1] / "static/chat-language.json").open(encoding="utf-8") as file:
    LANGUAGE = json.load(file)
WORD_ALIASES = LANGUAGE["word_aliases"]
PHOTO_WORDS = frozenset({"picture", "pictures", "photo", "photos", "image", "images", "pic", "pics"})

LOCATION_WORDS = frozenset({
    "arm", "arms", "leg", "legs", "face", "neck", "chest", "back",
    "hand", "hands", "foot", "feet", "scalp", "groin", "armpit", "armpits",
    "knee", "knees", "elbow", "elbows", "lip", "lips", "stomach", "abdomen",
    "shoulder", "shoulders", "forehead", "forearm", "forearms", "ankle", "ankles",
    "wrist", "wrists", "finger", "fingers", "toe", "toes", "ear", "ears",
    "cheek", "cheeks", "chin", "nose", "thigh", "thighs", "palm", "palms",
    "body", "everywhere", "head", "eye", "eyes", "jaw", "hip", "hips",
    "butt", "buttocks", "heel", "heels", "sole", "soles", "waist",
    "tongue", "mouth", "temple", "temples", "eyebrow", "eyebrows", "eyelid", "eyelids",
    "hairline", "collarbone", "calf", "calves", "shin", "shins", "nostril", "nostrils",
    "breast", "breasts", "nail", "nails", "genitals", "genital", "penis", "vulva",
})
DURATION_WORDS = frozenset({
    "minute", "minutes", "hour", "hours", "day", "days", "week", "weeks",
    "month", "months", "year", "years", "yesterday", "today", "ago", "since", "recently",
})
MEDICATION_WORDS = frozenset({
    "cream", "creams", "ointment", "ointments", "lotion", "medicine", "medication",
    "medications", "medicines", "drug", "gel", "steroid", "hydrocortisone",
    "antihistamine", "antibiotic", "prescription", "tablet", "tablets", "pill", "pills",
    "moisturizer", "moisturiser", "treatment", "treatments",
})
SYMPTOM_WORDS = frozenset({
    "itch", "itchy", "itching", "itchiness", "rash", "rashes", "red", "redness",
    "dry", "dryness", "flaky", "scaly", "bumps", "irritated", "irritation",
    "blister", "blisters", "burning", "peeling",
    "swollen", "swelling", "cracked", "cracking", "numb", "numbness", "sore", "sores",
    "wart", "warts", "mole", "moles", "spot", "spots", "spotty", "patch", "patches",
    "welts", "welt", "hives", "bumpy", "lump", "lumps", "oozing", "crusty", "crusting",
    "rough", "raw", "leathery", "waxy", "pale", "scaling", "pus", "bleeding", "tender",
    "tight", "flushing", "pain", "painful", "hurts", "discolored", "discoloured",
})
SEVERITY_WORDS = frozenset({
    'mild', 'moderate', 'severe', 'slight', 'manageable', 'significant', 'bad',
    'worse', 'worst', 'painful', 'pain', 'hurts', 'hurt', 'unbearable', 'intense', 'serious',
})


def normalize_message(message):
    text = unicodedata.normalize("NFKC", message).lower().replace("’", "'")
    text = text.replace("\u200b", "")
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*-?\s*(weeks?|wks?|weks|days?|dayz|months?|mos?|hours?|hrs?|years?|yrs?|minutes?|mins?)\b", r"\1 \2", text)
    text = re.sub(r"[a-z]+(?:'[a-z]+)?", lambda match: WORD_ALIASES.get(match.group(), match.group()), text)
    text = re.sub(r"\bhi{2,}\b", "hi", text)
    text = re.sub(r"\bhe+l{2,}o+\b", "hello", text)
    text = re.sub(r"\bhey+\b", "hey", text)
    text = re.sub(r"\b(can|could|may) i (sent|sending)\b", r"\1 i send", text)
    text = re.sub(r"\b(want|like|need) to (sent|sending)\b", r"\1 to send", text)
    text = re.sub(r"\bwhat (this|it|that) mean\b", r"what does \1 mean", text)
    text = re.sub(r"\b(cannot|could not) breath\b", r"\1 breathe", text)
    text = re.sub(r"\bi i do not know\b", "i do not know", text)
    return " ".join(text.split())


def clean_message(message):
    return normalize_message(message).strip().rstrip("?!.,")


def message_words(message):
    return set(re.findall(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", normalize_message(message)))


def is_photo_question(message):
    text = clean_message(message)
    if text in LANGUAGE["photo_result_questions"]:
        return True
    references = PHOTO_WORDS | {"result", "results", "it", "this", "that", "these", "those", "heatmap"}
    return bool(message_words(text) & references) and any(
        phrase in text for phrase in LANGUAGE["photo_question_phrases"]
    )


def is_explicit_photo_request(message):
    return bool(re.search(
        r"\b(?:(?:can|could|may) i|i (?:want|would like|need) to|let me|i am going to) "
        r"(?:send|upload|attach|share|show|submit)\b", clean_message(message)
    ))


def no_medication(message):
    text = clean_message(message)
    if re.search(r"\b(?:but|except|although|however|only|just|and)\b", text):
        return False
    # A mixed answer such as "no tablets, but I used a cream" is not "none".
    if re.search(r"\bi (?:have )?(?:used|use|tried|applied|took|take|am using)\b", text):
        return False
    if text in {
        "no", "none", "nothing", "nope", "not yet", "no medication", "no medicine",
        "no treatment", "i have not", "i did not", "i do not",
    }:
        return True
    return bool(re.search(
        r"\b(?:no (?:medication|medicine|cream|ointment|treatment)|(?:not|never) (?:use|used|using|take|taken|taking|try|tried|apply|applied))\b", text
    ))


def has_medication_answer(message):
    return no_medication(message) or bool(message_words(message) & MEDICATION_WORDS)


def has_duration_answer(message):
    """Require a timeframe; an alias such as 'mo' alone is not evidence."""
    text = clean_message(message)
    quantity = r'(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an|few|several|many|some|couple(?: of)?|half(?: a)?)'
    unit = r'(?:minutes?|hours?|days?|weeks?|months?|years?)'
    if re.search(r'\b' + quantity + r'\s+' + unit + r'\b', text):
        return True
    if re.search(r'\b(?:yesterday|today|recently)\b', text):
        return True
    if re.search(r'\b(?:last|this|past)\s+' + unit + r'\b', text):
        return True
    if re.search(r'\bsince\s+(?:\d{4}|monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december)\b', text):
        return True
    if re.search(r'\bsince (?:i was |my )?(?:a child|a teenager|little|childhood|birth|born)\b', text):
        return True
    if re.search(r'\b(?:for|been) (?:a while|some time|a long time)\b', text):
        return True
    # A full unit word can be a vague answer. A pronoun normalized to 'month'
    # inside another phrase ("lala mo") cannot.
    return bool(re.fullmatch(r'(?:days|weeks|months|years)(?: now)?', text))


def has_screening_evidence(intent, message):
    """A classifier score alone cannot establish a patient fact."""
    words = message_words(message)
    if intent == 'location':
        return bool(words & LOCATION_WORDS)
    if intent == 'duration':
        return has_duration_answer(message)
    if intent == 'severity':
        return bool(words & SEVERITY_WORDS) or bool(re.search(r'\b\d+ (?:out of|of) 10\b', clean_message(message)))
    if intent == 'symptom':
        return bool(words & SYMPTOM_WORDS)
    if intent == 'medication':
        return has_medication_answer(message) or bool(re.search(
            r'\bi (?:have (?:been )?)?(?:used|use|using|applied|took|take|tried|am using)\s+\S+', clean_message(message)
        ))
    return False
