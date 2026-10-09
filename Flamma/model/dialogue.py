"""Small conversation acts independent of the trained intent classifier."""

import re

from model.text_understanding import (
    LOCATION_WORDS, MEDICATION_WORDS, clean_message, message_words, no_medication,
)


SUMMARY_REQUESTS = {
    'summarize', 'summarise', 'summary', 'summarize our conversation',
    'summarise our conversation', 'what have i told you', 'what did i tell you',
    'what do you remember', 'what do you know about my skin', 'recap',
    'give me a summary', 'sum it up',
}
SIMPLE_REQUESTS = {
    'explain simply', 'explain it simply', 'explain in simple words',
    'say it simply', 'simple words please', 'make it simpler', 'make it shorter',
    'short version', 'in simple terms', 'explain again', 'i do not understand',
    'i do not get it', 'what do you mean', 'can you explain', 'could you explain',
    'simplify', 'in simpler words', 'keep it short', 'what does it mean', 'what does that mean',
}
PAUSE_REQUESTS = {
    'skip the questions', 'skip screening', 'stop asking questions',
    'no more questions', 'i do not want to answer questions',
    'i just want to talk', 'stop the screening',
}
RESUME_REQUESTS = {
    'continue screening', 'resume screening', 'ask me questions',
    'continue the screening', 'resume the screening',
}


def dialogue_act(message):
    text = clean_message(message).removesuffix(' please')
    if text in SUMMARY_REQUESTS or re.search(r'\b(?:summarize|summarise|recap)\b', text):
        return 'conversation_summary'
    if text in SIMPLE_REQUESTS or re.search(r'\b(?:simplify|simpler|simple words|simple terms|short version)\b', text):
        return 'simple_explanation'
    if text in PAUSE_REQUESTS:
        return 'screening_pause'
    if text in RESUME_REQUESTS:
        return 'screening_resume'
    return None


def looks_like_question(message):
    text = clean_message(message)
    return message.rstrip().endswith('?') or bool(re.search(
        r'\b(?:what (?:can|should|do|does|is|are)|how (?:can|do|does|to)|'
        r'why (?:is|does|do)|when should|should i|can (?:i|it|you|people)|'
        r'could (?:i|you)|is (?:it|this|that)|do i|does it|tell me|explain)\b', text
    ))


def is_self_report(message):
    return bool(re.search(r'\b(?:i (?:have|am experiencing|noticed|feel)|my (?:skin|rash|arm|face|leg))\b', clean_message(message)))


def is_medication_question(message):
    text = clean_message(message)
    return bool(re.search(r'\b(?:what|which|can|should|could|how)\b', text)) and bool(
        message_words(text) & {'cream', 'ointment', 'medicine', 'medication', 'dose', 'dosage', 'steroid'}
    )


def is_medication_report(message):
    text = clean_message(message)
    return bool(message_words(text) & MEDICATION_WORDS) and (
        no_medication(text) or bool(re.search(r'\bi (?:have )?(?:used|use|tried|applied|took|am using)\b', text))
    )


def concise(text):
    """Shorten existing knowledge without generating new medical claims."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    first = sentences[0]
    if ('depends' in first or 'vary depending' in first) and len(sentences) > 1:
        first += ' ' + sentences[1]
    return re.sub(r'\bdermatologist\b', 'skin doctor', first, flags=re.IGNORECASE)


def correction_updates(message):
    """Extract explicit replacements in order, excluding negated mentions."""
    text = clean_message(message)
    updates = {}

    def negated(start):
        return bool(re.search(r'\b(?:not|no|never)(?: (?:on|in|for|my|the|a|an)){0,3}\s*$', text[:start]))

    location_pattern = r'\b(?:(?:left|right) )?(?:' + '|'.join(sorted(LOCATION_WORDS, key=len, reverse=True)) + r')\b'
    locations = [match.group() for match in re.finditer(location_pattern, text) if not negated(match.start())]
    if locations:
        updates['location'] = ' and '.join(dict.fromkeys(locations))
    duration_pattern = (
        r'\b(?:(?:\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|a few|few|several|a|an) '
        r'(?:minutes?|hours?|days?|weeks?|months?|years?)|(?:since )?(?:yesterday|today))\b'
    )
    durations = [match.group() for match in re.finditer(duration_pattern, text) if not negated(match.start())]
    if durations and not is_medication_report(message):
        updates['duration'] = durations[-1]
    severities = [match.group() for match in re.finditer(r'\b(?:mild|moderate|severe)\b', text) if not negated(match.start())]
    if severities:
        updates['severity'] = severities[-1]
    if no_medication(text):
        updates['medication'] = 'none'
    elif message_words(text) & MEDICATION_WORDS and re.search(r'\bi (?:have )?(?:used|use|tried|applied|took|am using)\b', text):
        updates['medication'] = message
    return updates
