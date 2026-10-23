import json
import re
from pathlib import Path
from model.text_understanding import normalize_message, clean_message
from model.severity_support import severity_question


def is_course_question(message):
    """Recognize expected course without mistaking it for reported onset."""
    text = clean_message(message)
    if re.search(r'\bhow long (?:\w+ ){0,5}(?:(?:i|we|you) (?:use|apply|take)|to (?:use|apply|take))\b', text):
        return False
    return bool(re.search(
        r'\b(?:how (?:long|much time|soon|fast)|when)\b[^.;!?]{0,100}'
        r'\b(?:last|lasts|lasting|heal|heals|healing|clear|clears|recover|recovery|go away|get better|improve|resolve|settle)\b|'
        r'^(?:please )?(?:will|does)\b[^.;!?]{0,70}\b(?:last|heal|go away|clear up|improve|resolve)\b|'
        r'\b(?:recovery time|healing time|usual duration|typical duration)\b', text
    ))


TOPIC_PHRASES = {
    'symptoms': ('symptom', 'symptoms', 'sign', 'signs', 'look like', 'looks like'),
    'causes': ('cause', 'causes', 'caused', 'why', 'trigger', 'triggers', 'triggering', 'reason',
               'brings it on', 'brings this on', 'bring it on', 'leads to it',
               'sets it off', 'sets this off', 'makes it flare', 'makes this flare',
               'flare triggers', 'what brings on', 'what brings it on'),
    'contagious': ('contagious', 'infectious', 'catch it', 'catch this', 'catch that', 'catch eczema',
                   'catch psoriasis', 'catch dermatitis', 'pass it on', 'pass this on', 'spread to others',
                   'spread to people', 'spread to other people', 'spread to another person',
                   'give it to my partner', 'give it to my family', 'give it to other people',
                   'catch it from me', 'catch this from me', 'pass it to someone',
                   'pass it to other people', 'person to person', 'spread between people'),
    'management': ('treatment', 'treat', 'treated', 'treatable', 'treatability', 'manage', 'managed', 'manageable', 'management', 'care', 'medicine',
                   'medication', 'cure', 'cured', 'curable', 'controllable', 'controlled', 'cream', 'ointment', 'dose', 'dosage',
                   'what can i do', 'what should i do', 'what to do', 'what next', 'next steps',
                   'what now', 'how to help', 'help it', 'make it better',
                   'keep it under control', 'kept under control', 'bring it under control',
                   'anything that can help', 'anything i can do', 'next step',
                   'where do i start', 'where should i start'),
    'referral': ('doctor', 'dermatologist', 'hospital', 'clinic', 'professional', 'specialist',
                 'seek help', 'medical help', 'get it checked'),
}


def topic_requests(message):
    text = normalize_message(message)
    topics = [topic for topic, phrases in TOPIC_PHRASES.items() if any(
        re.search(r'\b' + re.escape(phrase) + r'\b', text) for phrase in phrases
    )]
    if is_course_question(message):
        topics.insert(0, 'course')
    if severity_question(message):
        topics.insert(0, 'severity')
    return topics


def is_disease_overview_question(message):
    text = normalize_message(message)
    return bool(re.search(
        r'\b(?:what (?:is|are) (?:(?:this|that|the|my) )?(?:skin )?(?:disease|condition)|'
        r'what (?:skin )?(?:disease|condition) (?:is|could) (?:this|that|it)|'
        r'(?:explain|describe) (?:(?:this|that|the|my) )?(?:skin )?(?:disease|condition)|'
        r'tell me about (?:(?:this|that|the|my) )?(?:skin )?(?:disease|condition))\b', text
    ))


def management_style(message):
    """Separate a short outcome question from a request for instructions."""
    text = normalize_message(message).strip().rstrip('?!.,').removesuffix(' please')
    if re.search(r'\b(?:curable|cure|cured)\b', text) and re.search(r'\b(?:is|can|will|does|are)\b', text):
        return 'curability'
    if re.search(r'\b(?:treatable|manageable|managed|controllable|controlled|kept under control)\b', text) or re.search(r'\bcan (?:it|this|that) be treated\b', text):
        return 'treatability'
    if re.fullmatch(r'(?:what (?:can|should) i do(?: (?:next|now))?|what next|what now|next steps?|where (?:do|should) i start)(?: (?:for|about|with) .+)?', text):
        return 'next_steps'
    return None


def is_diagnosis_question(message, has_named_condition=False):
    """Recognize requests to confirm the user's condition, not its definition."""
    text = normalize_message(message)
    if re.search(
        r'\b(?:is (?:this|that|it) (?:(?:really|actually) )?my (?:skin )?(?:condition|disease)|'
        r'do i (?:(?:really|actually|definitely) )?have (?:it|this|that)|'
        r'(?:does|would) (?:this|that|it) mean i (?:definitely )?have|'
        r'can you (?:confirm|diagnose|identify) (?:my (?:skin )?(?:condition|disease)|what i have)|'
        r'is (?:this|that|it) (?:a |the )?(?:diagnosis|confirmed diagnosis))\b', text
    ):
        return True
    if topic_requests(message) and re.match(r'(?:is|could|might) (?:this|that|it) (?:be )?(?:treatable|curable|contagious|infectious|manageable|caused|triggered)\b', text):
        return False
    return has_named_condition and bool(re.search(
        r'\b(?:do i (?:(?:really|actually|definitely) )?have|'
        r'(?:is|could|might) (?:this|that|it) (?:be )?(?:(?:really|actually|definitely) )?|'
        r'(?:confirm|diagnose) (?:my|me))\b', text
    ))


class KnowledgeBase:

    def __init__(self, path=None):

        path = path or Path(__file__).resolve().parents[1] / 'data/knowledge_base.json'

        with open(path, "r", encoding="utf-8") as file:
            self.data = json.load(file)
        with (Path(__file__).resolve().parents[1] / 'data/treatment_guidance.json').open(encoding='utf-8') as file:
            self.treatments = json.load(file)
        with (Path(__file__).resolve().parents[1] / 'data/course_guidance.json').open(encoding='utf-8') as file:
            self.courses = json.load(file)
        with (Path(__file__).resolve().parents[1] / 'data/severity_guidance.json').open(encoding='utf-8') as file:
            self.severities = json.load(file)
        self.aliases = {}
        for key, entry in self.data.items():
            for alias in [key.replace('_', ' '), entry['name'], *entry.get('aliases', [])]:
                self.aliases[normalize_message(alias)] = key

    def choices(self):
        return [entry['name'] for key, entry in self.data.items() if key != 'normal_skin']

    def is_condition_followup(self, message):
        text = clean_message(message).removesuffix(' please')
        match = re.fullmatch(r'(?:(?:how|what) about|and|same question for|what about treatment for) (.+?)(?: then)?', text)
        return bool(match and match.group(1) in self.aliases)

    # ==========================================================
    # DETECT DISEASE
    # ==========================================================

    def detect_disease(self, message):

        text = normalize_message(message)

        # Match a specific subtype before the broader word "dermatitis".
        for phrase in sorted(self.aliases, key=len, reverse=True):
            if re.search(r'\b' + re.escape(phrase) + r'\b', text.replace('_', ' ')):
                return self.aliases[phrase]

        return None

    def detect_diseases(self, message):
        """Find distinct names without counting a subtype's overlapping alias."""
        text = normalize_message(message).replace('_', ' ')
        found = []
        for phrase in sorted(self.aliases, key=len, reverse=True):
            for match in re.finditer(r'\b' + re.escape(phrase) + r'\b', text):
                if any(match.start() < end and match.end() > start for start, end, _ in found):
                    continue
                found.append((match.start(), match.end(), self.aliases[phrase]))
        diseases = list(dict.fromkeys(key for _, _, key in sorted(found)))
        # "Atopic dermatitis (eczema)" repeats a known alias rather than
        # proposing two alternatives. Explicit comparisons still keep both.
        if 'atopic_dermatitis' in diseases and 'dermatitis' in diseases and not re.search(r'\b(?:or|versus|vs|other|compare|difference)\b', text):
            generic = [text[start:end] for start, end, key in found if key == 'dermatitis']
            if generic and all(phrase == 'eczema' for phrase in generic):
                diseases.remove('dermatitis')
        return diseases

    # ==========================================================
    # DETECT KNOWLEDGE TOPIC
    # ==========================================================

    def detect_topic(self, message):
        return next(iter(topic_requests(message)), "overview")

    # ==========================================================
    # GET KNOWLEDGE
    # ==========================================================

    def get(self, disease, topic):
        if topic == 'course':
            return (self.course_info(disease) or {}).get('text')

        disease_data = self.data.get(disease)

        if disease_data is None:
            return None

        return disease_data.get(topic)

    def course_info(self, disease):
        entry = self.courses['conditions'].get(disease)
        if entry is None or disease not in self.data:
            return None
        return dict(entry, condition_key=disease, condition=self.data[disease]['name'],
                    topic='course', source_checked_on=self.courses['source_checked_on'])

    def treatment_info(self, disease):
        entry = self.treatments['conditions'].get(disease)
        if entry is None or disease not in self.data:
            return None
        return dict(entry, condition_key=disease, condition=self.data[disease]['name'],
                    source_checked_on=self.treatments['source_checked_on'])

    def treatment_text(self, disease):
        info = self.treatment_info(disease)
        if info is None:
            return ''
        lines = ['General care:', *('- ' + item for item in info['self_care'])]
        if info['clinician_options']:
            lines.extend(['', 'Treatment options to discuss with a clinician:',
                          *('- ' + item for item in info['clinician_options'])])
        lines.extend(['', 'Getting checked: ' + info['seek_care']])
        if info['clinician_options']:
            lines.append('A photo alone cannot select a medicine, dose, or treatment plan for you.')
        return '\n'.join(lines)

    # ==========================================================
    # PARSE QUESTION
    # ==========================================================

    def parse_question(self, message):

        disease = self.detect_disease(message)
        topic = self.detect_topic(message)

        topics = topic_requests(message)
        if not topics and (is_disease_overview_question(message) or disease is not None):
            topics = ['overview', 'symptoms', 'management']
        return {
            "disease": disease,
            "topic": topic,
            "topics": topics or ["overview"],
        }
