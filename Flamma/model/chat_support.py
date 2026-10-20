"""Conversation support and scope checks; no disease inference."""

import re
from model.text_understanding import SYMPTOM_WORDS, MEDICATION_WORDS, clean_message, message_words


def unrelated_request(message):
    text = clean_message(message)
    if re.search(r'\b(?:face id|avatar skin|video game|cream colored sofa|cream-colored sofa|computer virus|office chair|social media|car dashboard)\b', text):
        return True
    outside = {'javascript', 'python', 'router', 'software', 'laptop', 'printer', 'spreadsheet',
               'database', 'coding', 'code', 'homework', 'geometry', 'equation', 'pancakes',
               'recipe', 'bread', 'restaurant', 'football', 'basketball', 'movie', 'novel',
               'planets', 'photosynthesis', 'telephone', 'volcano', 'weather', 'flight',
               'hotel', 'tax', 'loan', 'currency', 'stocks', 'chess', 'music', 'song', 'joke', 'jokes', 'birthday'}
    words = message_words(text)
    return bool(words & outside) and not bool(words & (SYMPTOM_WORDS | MEDICATION_WORDS | {'dermatitis', 'eczema', 'psoriasis', 'rosacea', 'lichen', 'hives'}))


def support_intent(message):
    text = clean_message(message)
    if re.search(r'\b(?:what (?:does|do) (?:the |your |this |that )?(?:confidence|scores?|percentages?|accuracy)|'
                 r'how accurate (?:are you|is (?:this|the) (?:chatbot|system|screening))|'
                 r'who can (?:see|access) my (?:data|photos|messages|chats)|'
                 r'(?:is my (?:data|information|chat|photo)|are my (?:photos|messages|chats)) (?:secure|encrypted)|'
                 r'(?:do you|does (?:this|the) app) (?:encrypt|protect|secure)|'
                 r'what does \d+(?:\.\d+)?\s*% (?:accuracy|confidence|mean))\b', text):
        return 'bot_identity'
    if re.search(r'\b(?:i am (?:really |very |so )?(?:worried|scared|anxious|nervous)|this is worrying me|i feel (?:anxious|nervous|worried|scared))\b', text):
        return 'emotional_support'
    if re.search(r'\b(?:what (?:can you|can flamma|do you|does flamma) do|your (?:capabilities|purpose|limits)|how do you work|what are you|who are you|are you (?:a doctor|a dermatologist)|is (?:my information|my data|this chat) private|do you (?:save|store|learn)|where does your (?:information|knowledge) come from)\b', text):
        return 'bot_identity'
    return None


def confirmation_kind(message):
    text = clean_message(message)
    if re.search(r'\b(?:not sure|unsure|not certain|not completely certain|maybe)\b', text):
        return 'uncertain'
    if re.search(r'\b(?:no|nope|wrong|incorrect|not correct|not what|does not describe)\b', text):
        return 'negative'
    return 'affirmative'


def emotional_only(message):
    """Recognize a plain worry statement without suppressing physical warnings."""
    return bool(re.fullmatch(
        r'(?:i am (?:really |very |so )?(?:worried|scared|anxious|nervous)|i feel (?:anxious|nervous|worried|scared)|this is worrying me)'
        r'(?: about (?:this|that|it|my skin|my rash|my skin concern))?', clean_message(message)
    ))
