"""Small conversation acts independent of the trained intent classifier."""

import re

from model.text_understanding import (
    LOCATION_WORDS, MEDICATION_WORDS, clean_message, message_words, no_medication,
    duration_mentions, location_mentions,
)


SUMMARY_REQUESTS = {
    'summarize', 'summarise', 'summary', 'summarize our conversation',
    'summarise our conversation', 'what have i told you', 'what did i tell you',
    'what do you remember', 'what do you know about my skin', 'recap',
    'give me a summary', 'sum it up',
    'what do you remember about me', 'what do you remember about my skin',
}
SIMPLE_REQUESTS = {
    'explain simply', 'explain it simply', 'explain in simple words',
    'say it simply', 'simple words please', 'make it simpler', 'make it shorter',
    'short version', 'in simple terms', 'explain again', 'i do not understand',
    'i do not get it', 'what do you mean', 'can you explain', 'could you explain',
    'simplify', 'in simpler words', 'keep it short', 'what does it mean', 'what does that mean',
    'shorter', 'a shorter explanation', 'explain more simply',
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
    command = re.sub(r'^(?:please |(?:can|could|would) (?:you|we) (?:please )?)', '', text)
    command = command.removeprefix('please ')
    if re.fullmatch(r'(?:give me (?:a |the )?(?:summary|recap|gist)|sum up)(?: of (?:our|this|the) (?:chat|conversation))?', command):
        return 'conversation_summary'
    if re.fullmatch(r'(?:put (?:it|this|that) in plain english|explain (?:it|this|that) in (?:plain english|everyday language)|use (?:plain english|everyday language)|break (?:it|this|that) down(?: for me)?)', command):
        return 'simple_explanation'
    if re.fullmatch(r'(?:do not (?:stop|pause|skip) (?:asking )?(?:the )?(?:questions|screening)|keep (?:asking questions|going with the screening))', command):
        return 'screening_resume'
    if re.fullmatch(r'(?:hold off on|take a break from) (?:the )?(?:questions|screening)', command):
        return 'screening_pause'
    if re.fullmatch(r'(?:carry on with|get back to|go back to) (?:the )?(?:questions|screening)', command):
        return 'screening_resume'
    if re.fullmatch(r'i (?:would rather|prefer to|would prefer to) (?:chat|continue|talk) without (?:a |an )?(?:photo|picture|image)', text):
        return 'image_declined'
    if text in {'text only', 'text-only', 'i prefer text', 'let us chat without a photo', 'no photo',
                'i do not have a photo', 'i do not have a picture', 'i want to chat without a photo'}:
        return 'image_declined'
    if text in SUMMARY_REQUESTS or re.search(r'\b(?:summarize|summarise|recap)\b', text):
        return 'conversation_summary'
    if text in SIMPLE_REQUESTS or re.search(r'\b(?:simplify|simpler|simple words|simple terms|short version)\b', text):
        return 'simple_explanation'
    if re.search(r'\bdo not (?:want to )?(?:skip|pause|stop) (?:the )?screening\b', text):
        return 'screening_resume'
    if text in PAUSE_REQUESTS or re.search(r'\b(?:skip|pause|stop) (?:the )?screening\b', text):
        return 'screening_pause'
    if text in RESUME_REQUESTS or re.search(r'\b(?:continue|resume|restart) (?:the )?questions\b', text):
        return 'screening_resume'
    if text in {'new concern', 'new skin concern', 'new skin problem', 'another skin problem',
                'different skin concern', 'start a new concern', 'start a new skin concern'} or re.search(
        r'\b(?:i (?:have|noticed|am experiencing)|this is|there is|i want to discuss) '
        r'(?:(?:a|an) )?(?:new|different|another) (?:rash|skin (?:problem|concern|issue|condition))\b', text
    ):
        return 'new_concern'
    return None


def looks_like_question(message):
    text = clean_message(message)
    return message.rstrip().endswith('?') or bool(re.search(
        r'\b(?:what (?:can|should|do|does|is|are|brings|helps|makes)|how (?:can|do|does|to|long)|'
        r'why (?:is|does|do)|when should|should i|can (?:i|it|you|people)|'
        r'could (?:i|you|we)|would (?:you|it)|is (?:it|this|that|there)|do i|does it|tell me|explain)\b', text
    ))


def is_self_report(message):
    return bool(re.search(r'\b(?:i (?:have|am experiencing|noticed|feel)|my (?:skin|rash|arm|face|leg))\b', clean_message(message)))


SPECIFIC_MEDICINES = frozenset({'hydrocortisone', 'tacrolimus', 'pimecrolimus', 'metronidazole', 'ivermectin', 'azelaic'})


def is_medication_question(message):
    text = clean_message(message)
    return looks_like_question(message) and bool(re.search(r'\b(?:what|which|can|should|could|how|where|may|would)\b', text)) and bool(
        message_words(text) & (MEDICATION_WORDS | SPECIFIC_MEDICINES | {'dose', 'dosage'})
    )


def is_medication_report(message, mentioned_product=None):
    text = clean_message(message)
    reference = mentioned_product and medication_use_reference(message)
    negative_anything = no_medication(text) and re.search(r'\b(?:used|use|using|tried|try|applied|apply|taken|take) (?:anything|nothing)\b', text)
    known_name = mentioned_product and re.search(r'(?<!\w)' + re.escape(clean_message(mentioned_product)) + r'(?!\w)', text)
    return bool(reference or negative_anything) or bool(known_name or message_words(text) & (MEDICATION_WORDS | SPECIFIC_MEDICINES)) and (
        no_medication(text) or bool(re.search(r'\bi (?:(?:have|had) (?:been )?|am |was )?(?:used|use|using|tried|trying|applied|applying|took|take|taking|put|putting)\b', text))
    )


def medication_use_reference(message):
    return bool(re.search(
        r'\bi (?:(?:have|had)(?: not)? (?:been )?|(?:am|was)(?: not)? |do not |did not |never )?'
        r'(?:used|use|using|tried|trying|applied|applying|took|take|taking|put|putting) (?:it|that|this)'
        r'(?=\s*(?:$|[.,;!?])|\s+(?:on|for|yesterday|today|last|since|at|in|before|after|and|but|once|twice|daily|every)\b)',
        clean_message(message),
    ))


def medication_report_parts(message, mentioned_product=None):
    """Separate explicit self-report clauses; never infer rash facts from use sites."""
    clauses = [part.strip(' ,') for part in re.split(
        r'[.;]\s*|,\s*(?=(?:I|i|My|my)\b)|\band\s+(?=(?:I|i|My|my)\b)', message
    ) if part.strip(' ,')]
    medication = [part for part in clauses if is_medication_report(part, mentioned_product)]
    from model.text_understanding import symptom_mentions
    skin = [part for part in clauses if part not in medication and is_self_report(part)
            and symptom_mentions(part)[0] and not looks_like_question(part)]
    if not medication or (not skin and not any(looks_like_question(part) for part in clauses if part not in medication)):
        return [], message
    return skin, '; '.join(medication)


def concise(text):
    """Shorten existing knowledge without generating new medical claims."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    first = sentences[0]
    if ('depends' in first or 'vary depending' in first) and len(sentences) > 1:
        first += ' ' + sentences[1]
    return re.sub(r'\bdermatologist\b', 'skin doctor', first, flags=re.IGNORECASE)


def correction_updates(message, mentioned_product=None):
    """Extract explicit replacements in order, excluding negated mentions."""
    text = clean_message(message)
    updates = {}

    def negated(start):
        return bool(re.search(r'\b(?:not|no|never)(?: (?:on|in|for|my|the|a|an)){0,3}\s*$', text[:start]))

    locations = [match.group() for match in location_mentions(text) if not negated(match.start())]
    if locations and not is_medication_report(message, mentioned_product):
        updates['location'] = ' and '.join(dict.fromkeys(locations))
    durations = [match.group() for match in duration_mentions(text) if not negated(match.start())]
    if durations and not is_medication_report(message, mentioned_product):
        updates['duration'] = durations[-1]
    severities = [match.group() for match in re.finditer(r'\b(?:mild|moderate|severe)\b', text) if not negated(match.start())]
    if severities:
        updates['severity'] = severities[-1]
    if no_medication(text):
        updates['medication'] = 'none'
    elif is_medication_report(message, mentioned_product):
        updates['medication'] = message
    return updates
