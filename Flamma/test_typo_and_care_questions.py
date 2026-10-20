"""Regressions for the reported doctor question and informal English messages."""

import unittest
from unittest.mock import patch

from app import create_app
from model.safety import safety_intent
from model.text_understanding import normalize_message
from test_conversation_followups import patient_data
from test_image_integration import make_bot


class CareQuestionTests(unittest.TestCase):
    def test_doctor_questions_override_incorrect_emergency_guesses(self):
        for message in [
            'When should I see a doctor?', 'wen shud i see a docter?',
            'whn shld i c a dr?', 'Do I need a dermatologist?',
            'when to get medcial attention', 'should i go to a clinc',
        ]:
            with self.subTest(message=message):
                bot = make_bot()
                with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
                    reply = bot.reply(message)
                self.assertEqual(reply['intent'], 'knowledge_question')
                self.assertIn('Seek medical care promptly if', reply['reply'])
                self.assertNotIn('Please seek emergency medical care now', reply['reply'])
                self.assertNotIn('upload a photo', reply['reply'])
                self.assertFalse(bot.conversation.get('screening_paused'))
                self.assertEqual(bot.conversation.get('symptoms'), [])
                self.assertIsNone(bot.conversation.get('classification'))

    def test_suggested_question_works_with_named_condition_and_preserves_it(self):
        bot = make_bot()
        bot.reply('What is psoriasis?')
        self.assertIn('When should I see a doctor?', bot.suggested_questions())
        with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
            reply = bot.reply('When should I see a doctor?')
        self.assertEqual(reply['intent'], 'knowledge_question')
        self.assertIn('For Psoriasis:', reply['reply'])
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'psoriasis')
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertIn('General information about Psoriasis', bot.reply('and treatment?')['reply'])

    def test_general_care_advice_survives_failed_or_normal_photo(self):
        for status in ['rejected', 'normal_skin']:
            bot = make_bot()
            if status == 'rejected':
                bot.conversation.invalidate_image_result('Unclear image')
            else:
                bot.receive_classification('normal_skin', .8)
            reply = bot.reply('When should I see a doctor?')
            self.assertIn('Seek medical care promptly if', reply['reply'])
            self.assertNotIn('upload a photo', reply['reply'])

    def test_care_question_keeps_patient_facts_and_pending_question(self):
        bot = make_bot()
        bot.reply('my skin is itchy on my arm')
        before = patient_data(bot)
        self.assertEqual(bot.conversation.get('pending_question'), 'duration')
        bot.reply('When should I see a doctor?')
        self.assertEqual(patient_data(bot), before)
        self.assertEqual(bot.conversation.get('pending_question'), 'duration')
        self.assertEqual(bot.reply('2weks')['intent'], 'duration')

    def test_actual_warning_in_doctor_question_still_wins(self):
        for message, expected in [
            ('wen shud i see a docter? my lips are swolen', 'emergency'),
            ('Should I see a doctor? I cant brethe', 'emergency'),
            ('When should I see a doctor? My rash has pus and fver', 'medical_attention'),
        ]:
            self.assertEqual(make_bot().reply(message)['intent'], expected)

    def test_general_knowledge_does_not_turn_into_a_learned_emergency(self):
        bot = make_bot()
        with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
            self.assertEqual(bot.reply('whta is psorisis?')['intent'], 'knowledge_question')


class TypoUnderstandingTests(unittest.TestCase):
    def test_multi_turn_typo_answers_keep_original_text(self):
        bot = make_bot()
        bot.reply('myskin is ithcy on my elbwo')
        self.assertEqual(bot.conversation.get('location'), 'myskin is ithcy on my elbwo')
        self.assertIn('myskin is ithcy on my elbwo', bot.conversation.get('symptoms'))
        self.assertEqual(bot.reply('sicne 3dasy')['intent'], 'duration')
        duration = bot.conversation.get('duration')
        message = 'I have been using oinment for 2dasy'
        self.assertEqual(bot.reply(message)['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), message)
        self.assertEqual(bot.conversation.get('duration'), duration)

    def test_warning_typos_and_negation_have_different_meanings(self):
        for message in ['i cant brethe', 'cantbrethe', 'my thorat is swolen',
                        'my tounge swelled up', 'it is hard to breathe',
                        'i have truble swalowing', 'i have dificulty breatihng']:
            self.assertEqual(safety_intent(message), 'emergency', message)
        for message in ['i dnt have truble brething', 'my lips are not swolen',
                        'I donot have dificulty swalowing', 'i can breathe normally']:
            self.assertEqual(safety_intent(message, 'emergency'), 'safety_information', message)

    def test_curly_apostrophes_names_strengths_and_negation_are_preserved(self):
        for message in ["I\u2019m not having truble brething", "I\u2018m not having truble brething"]:
            self.assertEqual(normalize_message(message), 'i am not having trouble breathing')
        self.assertIn('tacrolimus 0.1%', normalize_message('Tacrolimus 0.1% oinment'))
        self.assertEqual(normalize_message('Nivolumab acetaminophen vitamin C armchair'),
                         'nivolumab acetaminophen vitamin c armchair')

    def test_medication_typo_is_not_recorded_as_a_treatment_report_in_question(self):
        bot = make_bot()
        reply = bot.reply('can i use this oinment?')
        self.assertEqual(reply['intent'], 'product_clarification')
        self.assertIsNone(bot.conversation.get('medication'))

    def test_http_route_preserves_original_messages_and_corrects_the_intent(self):
        bot = make_bot()
        app = create_app(bot, history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        message = 'wen shud i see a docter?'
        with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
            result = app.test_client().post('/predict', json={'message': message})
        self.assertEqual(result.status_code, 200)
        data = result.get_json()
        self.assertEqual(data['intent'], 'knowledge_question')
        self.assertEqual(data['messages'][0]['text'], message)


if __name__ == '__main__':
    unittest.main()
