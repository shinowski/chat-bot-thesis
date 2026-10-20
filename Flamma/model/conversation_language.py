"""Bounded conversation cues; these do not infer a disease or treatment."""

import re

from model.text_understanding import clean_message
from model.dialogue import is_medication_report, looks_like_question


def uncertainty_detail(message):
    text = clean_message(message)
    match = re.fullmatch(
        r'(?:i (?:do not|cannot) (?:know|remember|recall)|i am not sure|not sure|i forgot|(?:i have )?no idea)\s+(.+)', text
    )
    if not match:
        return False, None
    detail = match.group(1)
    if re.search(r'\b(?:how long|when (?:it|this|the (?:rash|problem)) (?:first )?(?:started|began|appeared)|duration|onset date)\b', detail):
        return True, 'duration'
    if re.search(r'\b(?:which (?:body )?(?:area|part)|where (?:it|this|the (?:rash|problem)) (?:is|started)|where on my body|location)\b', detail):
        return True, 'location'
    if re.search(r'\b(?:how (?:bad|severe|serious)|severity)\b', detail):
        return True, 'severity'
    if re.search(r'\b(?:what i (?:used|applied|took)|(?:what|which) (?:cream|medicine|medication|ointment|product|treatment) i (?:used|applied|took))\b', detail):
        return True, 'medication'
    if re.fullmatch(r'(?:what|which) (?:cream|medicine|medication|ointment|product|treatment) (?:it|this|that) (?:was|is)', detail):
        return True, None
    return False, None


def is_symptom_update(message, mentioned_product=None):
    if looks_like_question(message) or is_medication_report(message, mentioned_product):
        return False
    subjects = r'skin|rash|itch|itching|redness|dryness|flaking|stinging|tingling|irritation'
    text = re.sub(r"\b(" + subjects + r")'s\b", r'\1 has', clean_message(message))
    return bool(re.match(
        r'^(?:(?:my|the) (?:' + subjects + r')|it|this) '
        r'(?:(?:is|are|has|have|feels|looks|seems|was) (?:been )?)?'
        r'(?:(?:getting|got|gotten|become) (?:better|worse)|improving|improved|worsening|worse|better|'
        r'still (?:itchy|red|dry|flaky)|stopped|gone away|settled|no longer (?:itches|itchy)|'
        r'less (?:itchy|red)|more (?:itchy|red)|cleared(?: up)?|clearing up|'
        r'come back|returned|flaring up|flared up|comes and goes|eased|easing|'
        r'calmed down|settling down|no longer (?:stings|tingles)|'
        r'not (?:getting better|improving|cleared(?: up)?|easing|settling down))\b', text
    ))
