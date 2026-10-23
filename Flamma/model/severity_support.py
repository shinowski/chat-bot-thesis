"""Guided symptom-burden discussion, not diagnosis or a clinical severity score."""
import re
from model.text_understanding import clean_message, normalize_message, message_words, LOCATION_WORDS, DURATION_WORDS
from model.safety import _matches


QUESTIONS = {
    'sites': "Which body areas are affected? Include any scalp, face, hands, feet, nails or genital involvement. You can say 'I'm not sure.'",
    'extent': "About how much skin is affected? For psoriasis, estimate how many of your own whole handprints (palm, fingers and thumb together) would cover all the patches. A rough estimate or 'I'm not sure' is fine.",
    'impact': "How is it affecting you: is the itch disturbing sleep, work, school or everyday activities? You can also rate the itch from 0 to 10, or say you are not sure.",
    'joints': "Have you noticed any new joint pain, joint swelling or morning stiffness? You can answer yes, no, or 'I'm not sure.'",
}
OPTIONS = {
    'sites': ["I'm not sure", 'Stop severity questions'],
    'extent': ["I'm not sure", 'Stop severity questions'],
    'impact': ['It affects my sleep', 'No effect on daily activities', "I'm not sure", 'Stop severity questions'],
    'joints': ['Yes, new joint stiffness', 'No joint symptoms', "I'm not sure", 'Stop severity questions'],
}
DETAIL_LABELS = {
    'type': 'Reported dermatitis type or trigger', 'flares': 'Flare pattern',
    'exposure': 'Possible contact exposure (user report)', 'special_sites': 'Mouth, genital, scalp or nail changes',
    'eyes': 'Eye symptoms', 'pattern': 'Welt duration and recurrence',
}
DETAIL_WORDS = {
    'type': r'\b(?:atopic|contact|eczema|dermatitis|type|diagnosed|clinician|doctor|soap|product|trigger|none|no)\b',
    'flares': r'\b(?:flare|flares|comes|goes|recur|recurs|recurring|constant|daily|days?|weeks?|months?|present|always|sometimes|between|most|no|none)\b',
    'exposure': r'\b(?:product|soap|detergent|gloves?|metal|nickel|plant|perfume|fragrance|jewelry|jewellery|cleaner|cleaning|cosmetic|makeup|material|work|contact|exposure|exposed|new|no|none|stopped|continuing)\b',
    'special_sites': r'\b(?:mouth|gums?|genitals?|nails?|scalp|hair|hairline|soreness|sore|split|splitting|lifting|no|none|changes)\b',
    'eyes': r'\b(?:eyes?|eyelids?|dry|gritty|irritated|blurred|blurry|vision|light|sensitivity|no|none)\b',
    'pattern': r'\b(?:welts?|hours?|days?|weeks?|months?|last|lasts|fades?|fading|recur|recurs|appearing|daily|nightly|no|none)\b|\d',
}


def condition_entry(guidance, disease):
    entry = guidance.get(disease)
    return entry if isinstance(entry, dict) and 'overview' in entry else guidance['general']


def discussion_fields(entry, disease):
    return entry.get('fields', ['sites', 'extent', 'impact', *(['joints'] if disease == 'psoriasis' else [])])


def next_question(entry, disease, field):
    if field in entry.get('questions', {}):
        return entry['questions'][field]
    if field == 'extent' and disease != 'psoriasis':
        return 'Is the affected skin limited to a few small areas or spread over several body areas? A description or "I am not sure" is fine.'
    return QUESTIONS[field]


def answer_options(field):
    return OPTIONS.get(field, ["I'm not sure", 'Stop severity questions'])
UNKNOWN = {'i do not know', 'i dont know', 'not sure', 'i am not sure', 'i m not sure', 'unsure', 'no idea', 'skip', 'idk', 'i cannot estimate'}
STOP = {'stop severity questions', 'stop discussing severity', 'cancel severity questions'}


def severity_question(message):
    text = clean_message(normalize_message(message))
    if re.match(r'^(?:i (?:do not|cannot) know|i am not sure|not sure|i have no idea)\b', text):
        return False
    text = re.sub(r'\b(?:severety|sevrity|severtiy)\b', 'severity', text)
    return text in {'severity', 'and severity', 'what about severity', 'how about severity',
                    'continue severity questions', 'resume severity questions'} or bool(re.search(
        r'\b(?:how (?:\w+ ){0,9}(?:severe|serious|bad)|'
        r'(?:assess|assessment of|judge|measure|determine|check|know|tell|understand|rate) (?:\w+ ){0,8}severity|'
        r'(?:is|would|could) (?:my|this|that|it|the) (?:\w+ ){0,6}(?:mild|moderate|severe|serious)|'
        r'(?:what|which) (?:\w+ ){0,5}severity|'
        r'(?:mild|moderate) or severe)\b', text))


def uncertainty(message):
    text = clean_message(normalize_message(message)).replace("'", '')
    return text in UNKNOWN or bool(re.match(r'^(?:i (?:do not|cannot) know|i am not sure|not sure|i have no idea)\b', text))


def discussion_route(message, conversation):
    if severity_question(message):
        return True
    session = conversation.get('severity_discussion') or {}
    if not session.get('active'):
        return False
    text = clean_message(normalize_message(message))
    if text in STOP or uncertainty(message):
        return True
    if re.search(r'\b(?:what|why|how|when|can|should|could|would|treat|medicine|cream|ointment|used|using)\b', text):
        return False
    field = session.get('pending')
    words = message_words(text)
    if field == 'sites':
        return bool(words & LOCATION_WORDS) or text in {'none', 'nowhere', 'no symptoms', 'no skin changes'}
    if field == 'extent':
        return not bool(words & DURATION_WORDS) and bool(re.search(r'\b(?:handprints?|hands?|palms?|percent|percentage|small|large|patches?|spots?|widespread|couple|few|one|two|three|four|five|six|seven|eight|nine|ten|confined|limited|contact|facial|areas?|visible|changes|none|no)\b|\d|%', text))
    if field == 'impact':
        return bool(re.search(r'\b(?:itch|itchy|itching|sleep|sleeping|awake|wakes?|work|school|activities|daily|movement|walking|bothers|bothering|discomfort|mild|moderate|severe|effect|impact|burning|stinging|flushing|sore|soreness|eating|drinking|symptoms|none)\b|\d\s*(?:/|out of)', text))
    if field == 'joints':
        return bool(re.search(r'\b(?:yes|no|none|nope|yep|joint|joints|stiff|stiffness|knees?|fingers?|swelling)\b', text))
    if field in DETAIL_WORDS:
        return bool(re.search(DETAIL_WORDS[field], text))
    return False


def joint_report_positive(message):
    text = clean_message(normalize_message(message))
    if re.match(r'^(?:yes|yep|yeah)\b', text):
        return True
    for clause in re.split(r'\b(?:but|however)|[.;]', text):
        if re.search(r'\b(?:joint|joints|knees?|fingers?)\b', clause) and re.search(r'\b(?:pain|swelling|swollen|stiff|stiffness)\b', clause):
            if not re.search(r'\b(?:no|not|without|deny|never)\b', clause):
                return True
    return False


def burden_summary(session):
    labels = {'sites': 'Affected areas', 'extent': 'Extent estimate', 'impact': 'Symptoms and daily-life impact', 'joints': 'Joint symptoms', **DETAIL_LABELS}
    lines = ["Here is your symptom-burden summary (your descriptions, not a clinical severity grade):"]
    if session.get('condition_name'):
        lines.append('Condition discussed: ' + session['condition_name'] + ' (not a confirmed diagnosis from this chat).')
    lines.extend(labels.get(field, field) + ': ' + answer for field, answer in session.get('answers', {}).items())
    if session.get('joint_concern'):
        lines.append('You reported new joint symptoms. Arrange a clinician assessment; a chat cannot determine whether these are psoriatic arthritis.')
    impact = clean_message(session.get('answers', {}).get('impact', ''))
    if re.search(r'\b(?:cannot sleep|cant sleep|keeps me awake|wakes me|affects my sleep|cannot work|stops me)\b', impact):
        lines.append('You described disruption to sleep or daily activities. Discuss this impact with a clinician, even if the affected area seems small.')
    note = session.get('assessment_note')
    if note:
        lines.append(note)
    lines.append('A clinician needs to examine you to establish the condition and assess its severity. Small coverage or a high photo-model score cannot establish mild disease or rule out a more significant problem.')
    return '\n'.join(lines)


def eye_warning(message):
    text = normalize_message(message)
    clauses = re.split(r'[.;!?]|\b(?:but|however)\b', text)
    clauses = [clause for clause in clauses if not re.match(r'\s*(?:can|could|would|does|do|what|how|when|if|is|are|should)\b', clause)]
    return _matches(clauses, (r'eye pain', r'eyes? (?:hurt|hurting|ache|aching)',
                              r'(?:blurred|blurry|reduced) (?:eye ?sight|vision)',
                              r'(?:vision|eye ?sight) (?:is |has become |looks? )?(?:blurred|blurry)',
                              r'(?:light sensitivity|sensitive to light)', r'light hurts (?:my |the )?eyes?'))[0]


def discussion_alert(message, conversation):
    """Condition-specific warnings interrupt the optional questions."""
    text = normalize_message(message)
    session = conversation.get('severity_discussion') or {}
    disease = session.get('disease') if session.get('active') else None
    if re.search(r'\brosacea\b', text) or disease == 'rosacea':
        if eye_warning(message):
            return 'medical_attention', 'You described eye pain, vision changes or light sensitivity while discussing rosacea. Seek urgent medical advice for these eye symptoms; do not wait to finish the severity questions. A chat or skin photo cannot assess your eyes or confirm ocular rosacea.'
    if re.search(r'\b(?:hives|urticaria)\b', text) or disease == 'hives':
        clauses = [clause for clause in re.split(r'[.;!?]|\b(?:but|however)\b', text)
                   if not re.match(r'\s*(?:can|could|would|does|do|what|how|when|if|is|are|should)\b', clause)]
        if _matches(clauses, (r'(?:i feel|i am feeling|feeling) (?:very )?(?:faint|lightheaded|light headed)',
                               r'my heart (?:is racing|races)'))[0]:
            return 'emergency', 'Feeling faint or having a racing heart while experiencing hives can need emergency care. Seek emergency medical care now; do not wait to finish these questions or upload a photo.'
    return None


def guidance_reply(message, conversation, knowledge, disease=None, from_photo=False):
    """Keep discussion answers separate from screening severity and diagnosis."""
    guidance = knowledge.severities
    text = clean_message(normalize_message(message))
    session = conversation.get('severity_discussion') or {}
    if text in STOP:
        session = dict(session, active=False, pending=None)
        conversation.set('severity_discussion', session)
        return 'Sure. I have stopped the severity questions. You can ask another question or request a summary.', None, []
    named = knowledge.detect_disease(message)
    disease = named or disease or session.get('disease') or conversation.get('knowledge_disease')
    entry = condition_entry(guidance, disease)
    fields = discussion_fields(entry, disease)
    if disease == 'rosacea' and eye_warning(message):
        session = dict(session, disease=disease, active=False, pending=None,
                       condition_name=knowledge.data[disease]['name'],
                       answers={**session.get('answers', {}), 'eyes': message.strip()})
        conversation.set('severity_discussion', session)
        return ('You described eye pain, vision changes or light sensitivity. Seek urgent medical advice for these eye symptoms; do not wait to finish the severity questions. A chat or skin photo cannot assess your eyes or confirm ocular rosacea.',
                severity_info(guidance, knowledge, disease), ['When should I see a doctor?'])
    is_start = severity_question(message) or not session.get('active') or disease != session.get('disease')
    prefix = ''
    if is_start:
        if disease != session.get('disease') or not session:
            session = {'disease': disease, 'active': True, 'answers': {}, 'pending': fields[0]}
        else:
            session = dict(session, active=True)
            session['pending'] = next((field for field in fields if field not in session['answers']), None)
        session['condition_name'] = knowledge.data[disease]['name'] if disease in knowledge.data else None
        prefix = ('About the normal-skin screening label: ' if disease == 'normal_skin' else
                  'For ' + knowledge.data[disease]['name'].lower() + ': ' if disease in knowledge.data else
                  'About your skin concern: ') + entry['overview']
        if entry.get('extent_note'):
            prefix += '\n\n' + entry['extent_note']
        prefix += '\n\nI can help you describe these factors, but I cannot assign a clinical mild, moderate or severe grade from chat or a photo.'
        if from_photo:
            prefix += " Your photo's screening suggestion is not a confirmed diagnosis."
    else:
        field = session.get('pending')
        if field:
            if field == 'extent' and not uncertainty(message):
                quantities = re.findall(r'(?<![\w.])\d+(?:\.\d+)?', text)
                bounded_units = disease == 'psoriasis' or '%' in text or re.search(r'\b(?:percent|handprints?|palms?)\b', text)
                if re.search(r'\bor\b|(?:^|\s)-\d', text) or bounded_units and any(float(value) > 100 for value in quantities):
                    return 'Please give one rough estimate of coverage, or say you are not sure.\n\n' + next_question(entry, disease, field), severity_info(guidance, knowledge, disease), answer_options(field)
            session['answers'][field] = 'unknown' if uncertainty(message) else message.strip()
            if field == 'joints':
                session['joint_concern'] = not uncertainty(message) and joint_report_positive(message)
            session['pending'] = next((item for item in fields if item not in session['answers']), None)
            prefix = "I've recorded your description." if not uncertainty(message) else "That's okay. I've marked that detail as unknown."
    field = session.get('pending')
    if field:
        question = next_question(entry, disease, field)
        reply = prefix + '\n\n' + question
        options = answer_options(field)
    else:
        session['active'] = False
        if disease == 'lichen_planus':
            session['assessment_note'] = 'Discuss any mouth or genital symptoms, scalp hair loss or nail damage with a clinician; limited skin coverage does not exclude significant involvement at those sites.'
        elif disease == 'rosacea':
            session['assessment_note'] = 'New eye irritation needs clinician assessment. Eye pain, blurred vision or light sensitivity warrant urgent medical advice, even when facial skin changes seem small.'
        elif disease == 'hives':
            session['assessment_note'] = 'Discuss recurring or widespread hives with a clinician. Breathing or swallowing difficulty, mouth or throat swelling, or feeling faint require immediate medical care.'
        elif disease == 'normal_skin':
            session['assessment_note'] = 'The normal-skin screening label cannot explain away persistent or worsening symptoms or establish that no condition is present.'
        reply = burden_summary(session)
        options = ['When should I see a doctor?', 'Summarize our conversation']
    conversation.set('severity_discussion', session)
    if disease in knowledge.data and disease != 'normal_skin':
        conversation.set('knowledge_disease', disease)
    conversation.set('last_knowledge_topics', ['severity'])
    return reply, severity_info(guidance, knowledge, disease), options


def severity_info(guidance, knowledge, disease):
    entry = condition_entry(guidance, disease)
    return dict(condition_key=disease, condition=knowledge.data[disease]['name'] if disease in knowledge.data else 'Skin concern',
                topic='severity', sources=entry['sources'], source_checked_on=guidance['source_checked_on'])
