"""Reviewed vocabulary must improve understanding without inventing facts."""

import unittest
from unittest.mock import patch

from model.dialogue import dialogue_act
from model.knowledge_base import KnowledgeBase
from model.safety import safety_intent
from model.text_understanding import (
    has_duration_answer, normalize_message, symptom_mentions,
)
from test_image_integration import make_bot


class VocabularyTests(unittest.TestCase):
    def test_added_body_words_keep_the_original_report(self):
        for area in ['bellybutton', 'navel', 'tummy', 'torso', 'nape', 'underarms',
                     'knuckles', 'fingertips', 'jawline', 'earlobes', 'toenails']:
            with self.subTest(area=area):
                bot = make_bot()
                bot.reply('My skin is itchy')
                text = 'on my ' + area
                self.assertEqual(bot.reply(text)['intent'], 'location')
                self.assertEqual(bot.conversation.get('location'), text)
                self.assertIsNone(bot.conversation.get('classification'))

    def test_added_symptom_words_and_phrases_remain_reported_symptoms(self):
        for text in ['It stings', 'My skin is tingling', 'It is prickly',
                     'There is flaking', 'My skin is chapped', 'I have pins and needles']:
            with self.subTest(text=text):
                bot = make_bot()
                self.assertEqual(bot.reply(text)['intent'], 'symptom')
                self.assertEqual(bot.conversation.get('symptoms'), [text])
                self.assertIsNone(bot.conversation.get('knowledge_disease'))

    def test_negated_new_symptoms_do_not_become_positive(self):
        for symptom in ['stinging', 'tingling', 'pins and needles', 'flaking', 'puffiness']:
            self.assertEqual(symptom_mentions('I do not have ' + symptom), (set(), {symptom}))
        self.assertEqual(symptom_mentions('No tingling, but my skin stings'), ({'stings'}, {'tingling'}))

    def test_added_severity_words_do_not_assign_a_numeric_score(self):
        for word in ['bothersome', 'uncomfortable', 'tolerable', 'minimal', 'bearable']:
            bot = make_bot()
            bot.reply('My rash is on my arm for two weeks')
            text = 'It is ' + word
            self.assertEqual(bot.reply(text)['intent'], 'severity')
            self.assertEqual(bot.conversation.get('severity'), text)
            self.assertIsNone(bot.conversation.get('classification'))

    def test_more_time_expressions_preserve_the_report_without_calculating_dates(self):
        for text in ['twenty days', 'twenty-one days', 'thirteen months',
                     'a couple of nights', 'last night', 'this morning',
                     'since I woke up', 'overnight', 'half an hour', '3 dys']:
            self.assertTrue(has_duration_answer(text), text)
            bot = make_bot()
            bot.reply('I have a rash on my arm')
            self.assertEqual(bot.reply(text)['intent'], 'duration', text)
            self.assertEqual(bot.conversation.get('duration'), text)

    def test_unit_typo_requires_quantity_and_drugs_and_strengths_are_unchanged(self):
        self.assertEqual(normalize_message('I feel weak'), 'i feel weak')
        self.assertEqual(normalize_message('two weaks'), 'two weeks')
        self.assertEqual(normalize_message('Fortnite is a game'), 'fortnite is a game')
        text = 'Nivolumab Xylarose rosceazole 0.05% 2.5 mg'
        self.assertEqual(normalize_message(text), text.lower())

    def test_unfamiliar_answers_cannot_become_medical_facts_from_model_confidence(self):
        for intent, field in [('location', 'location'), ('duration', 'duration'),
                              ('severity', 'severity'), ('symptom', 'symptoms')]:
            bot = make_bot()
            with patch.object(bot.classifier, 'predict', return_value=(intent, .99)):
                bot.reply('florble zindango')
            self.assertIn(bot.conversation.get(field), (None, []))
            self.assertIsNone(bot.conversation.get('classification'))

    def test_polite_commands_and_their_negation(self):
        for text, expected in [
            ('Please hold off on the questions', 'screening_pause'),
            ('Could we carry on with the screening', 'screening_resume'),
            ("Please don't stop asking questions", 'screening_resume'),
            ('Could you give me the gist of our conversation', 'conversation_summary'),
            ('Would you break that down for me', 'simple_explanation'),
            ("I'd rather chat without a picture", 'image_declined'),
        ]:
            self.assertEqual(dialogue_act(text), expected, text)
        for text in ['Should I hold off on this cream?', 'I do not need plain English',
                     'A gist is a short summary of something']:
            self.assertIsNone(dialogue_act(text), text)

    def test_condition_switch_requires_a_complete_recognized_name(self):
        knowledge = KnowledgeBase()
        for text in ['and roseaca', 'same question for psoriosis', 'what about lichenplanus then']:
            self.assertTrue(knowledge.is_condition_followup(text), text)
        for text in ['and my arm is itchy', 'same question for an unknown illness',
                     'what about rosaceazole then', 'and roseaca or eczema']:
            self.assertFalse(knowledge.is_condition_followup(text), text)

    def test_added_contractions_keep_warning_denials_and_real_warnings_separate(self):
        self.assertEqual(safety_intent("My lips haven't swollen"), 'safety_information')
        self.assertEqual(safety_intent('My lips are swollon'), 'emergency')


if __name__ == '__main__':
    unittest.main()
