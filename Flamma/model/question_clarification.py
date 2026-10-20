"""Clarify references and conflicting details without inventing patient facts."""

import re
from model.text_understanding import clean_message, LOCATION_WORDS, normalize_message
from model.dialogue import SPECIFIC_MEDICINES, is_medication_question, is_medication_report, looks_like_question
from model.text_understanding import message_words, duration_mentions, location_mentions


def knowledge_choice_index(message):
    text = clean_message(message)
    match = re.fullmatch(r'(?:the )?(first|second|third|fourth|fifth|sixth|seventh|eighth|[1-8](?:st|nd|rd|th)?)(?: (?:one|condition|option))?', text)
    if not match:
        return None
    choice = match.group(1)
    if choice[0].isdigit():
        return int(choice[0]) - 1
    return ['first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'seventh', 'eighth'].index(choice)


def clarification_request(message, knowledge):
    text = clean_message(message)
    diseases = knowledge.detect_diseases(message)
    if len(diseases) > 1:
        comparison = re.search(r'\b(?:compare|comparison|difference|different from|versus|vs)\b', text)
        return ('condition_comparison' if comparison else 'condition_clarification', diseases)
    if is_medication_question(message) and re.search(r'\b(?:what|which) (?:\w+ ){0,2}(?:cream|ointment|medicine|medication|steroid|treatment)\b', text):
        return 'knowledge_question', []
    if is_medication_question(message) and message_words(message) & SPECIFIC_MEDICINES:
        return 'product_information', []
    if is_medication_question(message) and (
        re.search(r'\b(?:use|apply|take|try)\b', text) or re.search(r'\b(?:side effects?|risks?|dose|dosage)\b', text)
    ):
        return ('product_information' if message_words(message) & SPECIFIC_MEDICINES else 'product_clarification'), []
    if re.search(r'\b(?:can|should|could|may) i (?:use|apply|take|try) (?:it|this|that|these|those|the cream|the medicine|the ointment)\b', text):
        return 'product_clarification', []
    if not looks_like_question(message) and not is_medication_report(message) and re.search(r'\b(?:or|maybe|not sure|either)\b', text):
        durations = [match.group() for match in duration_mentions(message)]
        if len(set(durations)) > 1:
            return 'duration_clarification', durations
        locations = list(dict.fromkeys(match.group() for match in location_mentions(message)
                                      if match.group() not in {'body', 'everywhere'}))
        if len(locations) > 1:
            return 'location_clarification', locations
    if text in {'is it good', 'is it bad', 'is that good', 'is this okay', 'is that okay',
                'does that help', 'can i do that', 'what about that'}:
        return 'question_clarification', []
    return None


def bare_product_answer(message):
    text = clean_message(message)
    if re.match(r'^(?:hello|hey|hi|thank you|thanks|bye|yes|yeah|yep|no|nope|okay|ok)\b', text):
        return False
    return len(text) <= 160 and 0 < len(text.split()) <= 8 and not looks_like_question(message) and not is_medication_report(message)


def screening_choice_answer(message, choices):
    """Resolve short answers only against the last explicit screening choices."""
    if not choices or choices.get('field') not in {'location', 'duration'}:
        return None
    options = choices.get('options', [])
    index = knowledge_choice_index(message)
    if index is not None and index < len(options):
        return options[index]
    if choices['field'] == 'location' and clean_message(message) in {'both', 'both areas', 'both of them', 'all of them'} and options:
        return ' and '.join(options)
    return None


def explicit_fact_replacement(message):
    text = clean_message(message)
    if not re.match(r'^not\b', text) or not re.search(r',|\bbut\b|\binstead\b', text):
        return False
    from model.dialogue import correction_updates
    updates = correction_updates(message)
    return bool(updates.get('location') or updates.get('duration'))
