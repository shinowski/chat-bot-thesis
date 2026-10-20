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
PHOTO_REFERENCES = PHOTO_WORDS | {'result', 'results', 'heatmap'}

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
    "torso", "tummy", "belly", "bellybutton", "navel", "nape",
    "shoulderblade", "shoulderblades", "underarm", "underarms",
    "fingertip", "fingertips", "knuckle", "knuckles", "cuticle", "cuticles",
    "toenail", "toenails", "fingernail", "fingernails", "earlobe", "earlobes",
    "sideburn", "sideburns", "jawline", "midriff", "ribcage",
    "pubic", "perineum", "scrotum", "anus",
})
DURATION_WORDS = frozenset({
    "minute", "minutes", "hour", "hours", "day", "days", "week", "weeks",
    "month", "months", "year", "years", "yesterday", "today", "ago", "since", "recently",
    "night", "nights", "overnight", "fortnight", "fortnights",
})
DURATION_QUANTITY = r'(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|(?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:[ -](?:one|two|three|four|five|six|seven|eight|nine))?|a|an|few|several|many|some|couple(?: of)?|half(?: an?)?)'
DURATION_UNIT = r'(?:minutes?|hours?|days?|nights?|weeks?|months?|years?)'
DURATION_PATTERN = re.compile(
    r'(?<![\w-])(?:since )?(?:'
    r'(?:a )?' + DURATION_QUANTITY + r'(?:\s*(?:-|to)\s*' + DURATION_QUANTITY + r')?\s+'
    + DURATION_UNIT + r'(?: and a half)?|yesterday|today|last night|this (?:morning|afternoon|evening))'
    r'(?![\w-])'
)
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
    "stings", "stinging", "sting", "tingles", "tingling", "prickly", "scratchy",
    "itches", "flaking", "flakes", "flakiness", "scaliness", "blistering",
    "reddish", "soreness", "tenderness", "tightness", "cracks", "fissures",
    "crust", "crusts", "crustiness", "weeping", "puffiness", "puffy",
    "bruising", "bruises", "bruised", "discoloration", "discolouration",
    "inflamed", "inflammation", "chafing", "chafed", "chapped", "scabs", "scab",
    "thickened", "thickening", "blotchy", "blotches", "scarring", "scars",
})
SYMPTOM_PHRASES = ('pins and needles', 'raised patches', 'skin feels hot', 'skin feels warm')
SYMPTOM_PATTERN = re.compile(r'\b(?:' + '|'.join(
    re.escape(term) for term in sorted(SYMPTOM_WORDS | set(SYMPTOM_PHRASES), key=len, reverse=True)
) + r')\b')
SEVERITY_WORDS = frozenset({
    'mild', 'moderate', 'severe', 'slight', 'manageable', 'significant', 'bad',
    'worse', 'worst', 'painful', 'pain', 'hurts', 'hurt', 'unbearable', 'intense', 'serious',
    'uncomfortable', 'bothersome', 'tolerable', 'intolerable', 'excruciating',
    'agonizing', 'agonising', 'minimal', 'bearable',
})
LOCATION_PATTERN = re.compile(
    r'\b(?:(?:left|right|upper|lower|inner|outer|front|rear) ){0,2}(?:'
    + '|'.join(sorted(LOCATION_WORDS, key=len, reverse=True)) + r')\b'
)


def duration_mentions(message):
    """Return complete time phrases, including ranges; never calculate onset."""
    return list(DURATION_PATTERN.finditer(clean_message(message)))


def location_mentions(message):
    """Keep directional qualifiers attached to the body area they describe."""
    return list(LOCATION_PATTERN.finditer(clean_message(message)))


def normalize_message(message):
    text = unicodedata.normalize("NFKC", message).lower().replace("’", "'")
    text = text.replace("\u200b", "")
    text = text.replace("\u2018", "'")
    text = re.sub(r"[a-z]+(?:'[a-z]+)?", lambda match: WORD_ALIASES.get(match.group(), match.group()), text)
    # "Weak" is a real word. Correct the unit typo only after a quantity.
    text = re.sub(r'\b(\d+(?:\.\d+)?|one|two|three|four|five|six|a|several|few)\s+(weaks?)\b',
                  lambda match: match.group(1) + (' weeks' if match.group(2).endswith('s') else ' week'), text)
    text = re.sub(r"\b(\d+(?:\.\d+)?)\s*-?\s*(weeks?|days?|months?|hours?|years?|minutes?)\b", r"\1 \2", text)
    text = re.sub(r"\bhi{2,}\b", "hi", text)
    text = re.sub(r"\bhe+l{2,}o+\b", "hello", text)
    text = re.sub(r"\bhey+\b", "hey", text)
    text = re.sub(r"\b(can|could|may) i (sent|sending)\b", r"\1 i send", text)
    text = re.sub(r"\b(want|like|need) to (sent|sending)\b", r"\1 to send", text)
    text = re.sub(r"\bwhat (this|it|that) mean\b", r"what does \1 mean", text)
    text = re.sub(r"\b(cannot|could not) breath\b", r"\1 breathe", text)
    text = re.sub(r"\bi i do not know\b", "i do not know", text)
    text = re.sub(r"\b(should|could|can|must) i c (?=(?:a |the )?(?:doctor|dermatologist)\b)", r"\1 i see ", text)
    return " ".join(text.split())


def clean_message(message):
    return normalize_message(message).strip().rstrip("?!.,")


def message_words(message):
    return set(re.findall(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?", normalize_message(message)))


def negation_prefix(text):
    """Scope negation to symptoms rather than not using or getting treatment."""
    text = re.sub(r'\bnot sure\b', 'unsure', text)
    text = re.sub(r'\b(?:not|never) (?=(?:(?:yet|ever|been) ){0,2}(?:use|used|using|apply|applied|applying|take|taken|taking|try|tried|treat|treated|treating)\b)', ' ', text)
    return re.sub(r'\b(?:no|without) (?:any )?(?:cream|medicine|medication|ointment|treatment)\b', 'treatment', text)


def symptom_mentions(message):
    """Distinguish affirmative symptom words from locally negated mentions.

    Original wording remains the evidence; this does not identify a condition.
    Split contrast clauses so 'no rash, but my skin is dry' retains dry skin.
    """
    affirmative, denied = set(), set()
    text = normalize_message(message)
    clauses = re.split(r'[.;!?]+|\b(?:but|however|although|yet)\b|\band\s+(?=(?:my|i|he|she|his|her|their)\b)', text)
    for clause in clauses:
        for match in SYMPTOM_PATTERN.finditer(clause):
            word = match.group()
            prefix = negation_prefix(clause[:match.start()])
            negated = re.search(r'\b(?:no|not|never|without|deny|denies)\b(?:\s+\w+){0,6}\s*$', prefix)
            negated = negated or re.match(r'\s+(?:is|are)\s+not\s+(?:present|there|visible|happening)\b', clause[match.end():])
            (denied if negated else affirmative).add(word)
    return affirmative, denied


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
        "no i have not", "no i did not", "no i do not",
        "no, i have not", "no, i did not", "no, i do not",
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
    quantity, unit = DURATION_QUANTITY, DURATION_UNIT
    if re.search(r'\b' + quantity + r'\s+' + unit + r'\b', text):
        return True
    if re.search(r'\b(?:yesterday|today|recently)\b', text):
        return True
    if text == 'overnight' or re.search(r'\b(?:last night|this morning|this afternoon|this evening|since (?:breakfast|lunch|dinner|i woke up))\b', text):
        return True
    if re.search(r'\bfortnights?\b', text):
        return True
    if re.search(r'\b(?:last|this|past)\s+' + unit + r'\b', text):
        return True
    if re.search(r'\b(?:last|this|past)\s+(?:winter|spring|summer|autumn|fall|weekend)\b', text):
        return True
    if re.search(r'\bsince\s+(?:last\s+)?(?:\d{4}|monday|tuesday|wednesday|thursday|friday|saturday|sunday|january|february|march|april|may|june|july|august|september|october|november|december)\b', text):
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
        return bool(symptom_mentions(message)[0])
    if intent == 'medication':
        return has_medication_answer(message) or bool(re.search(
            r'\bi (?:have (?:been )?)?(?:used|use|using|applied|took|take|tried|am using)\s+\S+', clean_message(message)
        ))
    return False
