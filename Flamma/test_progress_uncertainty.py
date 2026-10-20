"""Updates, unknown answers, and warning reports must retain their scope."""

import json
import unittest
from unittest.mock import patch

from app import create_app
from model.context_intent import ContextIntent
from model.conversation_language import uncertainty_detail, is_symptom_update
from model.safety import safety_intent
from test_image_integration import make_bot


class ProgressUncertaintyTests(unittest.TestCase):
    def test_specific_duration_uncertainty_keeps_an_unanswered_location(self):
        bot = make_bot()
        bot.reply('My skin is itchy')
        with patch.object(bot.classifier, 'predict', return_value=('duration', .99)):
            result = bot.reply("I don't know how long it's been there")
        self.assertEqual(result['intent'], 'uncertain_answer')
        self.assertEqual(bot.conversation.get('duration'), 'unknown')
        self.assertIsNone(bot.conversation.get('location'))
        self.assertEqual(bot.conversation.get('pending_question'), 'location')
        bot.reply('my elbow')
        self.assertEqual(bot.conversation.get('pending_question'), 'medication')

    def test_each_specific_unknown_answer_sets_only_its_field(self):
        for text, field in [("I can't remember when it started", 'duration'),
                            ("I'm not sure which body area is affected", 'location'),
                            ("I don't know how severe it is", 'severity'),
                            ("I can't remember what medicine I used", 'medication')]:
            bot = make_bot()
            bot.reply('My skin is itchy')
            self.assertEqual(bot.reply(text)['intent'], 'uncertain_answer', text)
            self.assertEqual(bot.conversation.get(field), 'unknown', text)
            for other in {'duration', 'location', 'severity', 'medication'} - {field}:
                self.assertIsNone(bot.conversation.get(other), (text, other))

    def test_unknown_product_name_keeps_the_question_and_does_not_record_use(self):
        bot = make_bot()
        bot.reply('Can I use that cream?')
        result = bot.reply("I can't remember what cream it was")
        self.assertEqual(result['intent'], 'uncertain_answer')
        self.assertIsNone(bot.conversation.get('medication'))
        self.assertIsNone(bot.conversation.get('mentioned_product'))
        self.assertEqual(bot.reply('CeraVe')['intent'], 'product_information')
        self.assertIsNone(bot.conversation.get('medication'))

    def test_non_screening_unknown_phrases_do_not_skip_patient_fields(self):
        for text in ["I don't know why rosacea happens", "I don't know how to cook pancakes"]:
            self.assertEqual(uncertainty_detail(text), (False, None))
            self.assertFalse(ContextIntent.is_uncertain(text))

    def test_symptom_change_today_does_not_replace_original_duration_or_treatment(self):
        for text in ['It is getting better today', 'The redness is worse today',
                     'The itching has stopped', 'My skin is still itchy',
                     "It's getting better today", "The itching's gone away", 'It has gotten better']:
            bot = make_bot()
            report = 'My rash is on my arm for two weeks'
            bot.reply(report)
            bot.reply('I used a cream for three days')
            result = bot.reply(text)
            self.assertEqual(result['intent'], 'symptom_update', text)
            self.assertEqual(bot.conversation.get('duration'), report)
            self.assertEqual(bot.conversation.get('location'), report)
            self.assertEqual(bot.conversation.get('medication'), 'I used a cream for three days')
            self.assertEqual(bot.conversation.get('symptom_updates'), [text])
            self.assertEqual(bot.conversation.get('symptoms'), [report])
            self.assertIsNone(bot.conversation.get('classification'))

    def test_ended_symptom_does_not_become_a_new_current_positive_symptom(self):
        bot = make_bot()
        result = bot.reply('The itching has gone away')
        self.assertEqual(result['intent'], 'symptom_update')
        self.assertEqual(bot.conversation.get('symptoms'), [])
        self.assertIsNone(bot.conversation.get('duration'))
        self.assertIsNone(bot.conversation.get('knowledge_disease'))

    def test_change_questions_and_treatment_usage_are_not_status_reports(self):
        for text in ['What if my rash gets worse?', 'Is it getting better?',
                     'I used a cream and my skin is better', 'Will the itching stop?']:
            self.assertFalse(is_symptom_update(text), text)

    def test_updates_remain_reported_words_in_summary_and_survive_restore(self):
        bot = make_bot()
        bot.reply('My rash is on my arm for two weeks')
        bot.reply('It is getting better today')
        restored = make_bot()
        restored.conversation.restore(bot.conversation.data)
        summary = restored.reply('summarize our conversation')['reply']
        self.assertIn("Changes you've reported (your words): It is getting better today", summary)
        self.assertIn('How long: My rash is on my arm for two weeks', summary)
        restored.reply('new skin concern')
        self.assertEqual(restored.conversation.get('symptom_updates'), [])

    def test_update_does_not_resume_paused_screening(self):
        bot = make_bot()
        bot.reply('Skip the questions')
        bot.reply('It is getting better today')
        self.assertTrue(bot.conversation.get('screening_paused'))
        self.assertIsNone(bot.conversation.get('pending_question'))

    def test_saved_updates_retain_the_original_message_and_do_not_replace_rash_onset(self):
        app = create_app(make_bot(), history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        client.post('/predict', json={'message': 'My rash is on my arm for two weeks'})
        response = client.post('/predict', json={'message': 'It is getting better today'}).get_json()
        self.assertEqual(response['messages'][0]['text'], 'It is getting better today')
        state = json.loads(app.extensions['chat_history'].db.execute('SELECT state FROM conversations').fetchone()['state'])
        self.assertEqual(state['symptom_updates'], ['It is getting better today'])
        self.assertEqual(state['duration'], 'My rash is on my arm for two weeks')

    def test_not_treating_a_warning_sign_cannot_hide_it(self):
        for text in ["I haven't treated my swollen lips", 'I have not used cream for swollen lips',
                     'No cream for my swollen lips', 'I have never treated my swollen eyes',
                     'I have not yet treated my swollen lips', 'I have not been treating my swollen lips']:
            self.assertEqual(safety_intent(text), 'emergency', text)
            bot = make_bot()
            result = bot.reply(text)
            self.assertEqual(result['intent'], 'emergency')
            self.assertNotIn('treatmentInfo', result)

    def test_actual_denial_of_warning_sign_stays_a_denial(self):
        for text in ['My lips are not swollen', 'I do not have swollen lips',
                     'No swelling of my lips', 'I have never had swollen eyes']:
            self.assertEqual(safety_intent(text), 'safety_information', text)

    def test_current_warning_sign_wins_over_uncertainty_and_progress(self):
        for text in ["I don't know how long it's been there and I cannot breathe",
                     'My skin is getting better but my lips are swollen']:
            bot = make_bot()
            self.assertEqual(bot.reply(text)['intent'], 'emergency')
            self.assertEqual(bot.conversation.get('symptom_updates'), [])


if __name__ == '__main__':
    unittest.main()
