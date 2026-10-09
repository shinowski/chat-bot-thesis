import json
import re
from pathlib import Path
from model.text_understanding import normalize_message


TOPIC_PHRASES = {
    'symptoms': ('symptom', 'symptoms', 'sign', 'signs', 'look like', 'looks like'),
    'causes': ('cause', 'causes', 'caused', 'why', 'trigger', 'triggers', 'reason'),
    'contagious': ('contagious', 'infectious', 'catch it', 'catch this', 'catch that', 'catch eczema',
                   'catch psoriasis', 'catch dermatitis', 'pass it on', 'pass this on', 'spread to others',
                   'spread to people', 'spread to another person'),
    'management': ('treatment', 'treat', 'treated', 'manage', 'management', 'care', 'medicine',
                   'medication', 'cure', 'cured', 'cream', 'ointment', 'dose', 'dosage',
                   'what can i do', 'what should i do', 'what to do', 'what next', 'next steps',
                   'what now', 'how to help', 'help it', 'make it better'),
    'referral': ('doctor', 'dermatologist', 'hospital', 'clinic', 'professional', 'specialist',
                 'seek help', 'medical help', 'get it checked'),
}


def topic_requests(message):
    text = normalize_message(message)
    return [topic for topic, phrases in TOPIC_PHRASES.items() if any(
        re.search(r'\b' + re.escape(phrase) + r'\b', text) for phrase in phrases
    )]


def is_disease_overview_question(message):
    text = normalize_message(message)
    return bool(re.search(
        r'\b(?:what (?:is|are) (?:(?:this|that|the|my) )?(?:skin )?(?:disease|condition)|'
        r'what (?:skin )?(?:disease|condition) (?:is|could) (?:this|that|it)|'
        r'(?:explain|describe) (?:(?:this|that|the|my) )?(?:skin )?(?:disease|condition)|'
        r'tell me about (?:(?:this|that|the|my) )?(?:skin )?(?:disease|condition))\b', text
    ))


class KnowledgeBase:

    def __init__(self, path=None):

        path = path or Path(__file__).resolve().parents[1] / 'data/knowledge_base.json'

        with open(path, "r", encoding="utf-8") as file:
            self.data = json.load(file)
        self.aliases = {}
        for key, entry in self.data.items():
            for alias in [key.replace('_', ' '), entry['name'], *entry.get('aliases', [])]:
                self.aliases[normalize_message(alias)] = key

    def choices(self):
        return [entry['name'] for key, entry in self.data.items() if key != 'normal_skin']

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

    # ==========================================================
    # DETECT KNOWLEDGE TOPIC
    # ==========================================================

    def detect_topic(self, message):
        return next(iter(topic_requests(message)), "overview")

    # ==========================================================
    # GET KNOWLEDGE
    # ==========================================================

    def get(self, disease, topic):

        disease_data = self.data.get(disease)

        if disease_data is None:
            return None

        return disease_data.get(topic)

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
