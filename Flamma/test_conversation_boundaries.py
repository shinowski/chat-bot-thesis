"""Different skin concerns and symptom denials must not manufacture facts."""

import io
import unittest
from unittest.mock import patch

from werkzeug.datastructures import FileStorage
from app import create_app
from model.text_understanding import symptom_mentions
from test_image_integration import make_bot
from test_safety_and_reliability import PNG


class ConversationBoundaryTests(unittest.TestCase):
    def test_explicit_new_concern_clears_photo_and_old_screening_details(self):
        bot = make_bot()
        bot.reply('my rash is itchy on my arm for two weeks')
        bot.reply('I used a cream')
        bot.reply('', FileStorage(filename='skin.png'))
        result = bot.reply('I have a new rash on my left leg')
        self.assertEqual(result['intent'], 'new_concern')
        for field in ['classification', 'image_knowledge_key', 'image_condition', 'classification_image_id',
                      'classification_confidence', 'knowledge_disease', 'duration', 'medication']:
            self.assertIsNone(bot.conversation.get(field), field)
        self.assertFalse(bot.conversation.get('image_uploaded'))
        self.assertEqual(bot.conversation.get('symptoms'), ['I have a new rash on my left leg'])
        self.assertEqual(bot.conversation.get('pending_question'), 'duration')
        self.assertNotIn('treatmentInfo', result)
        self.assertNotIn('treatmentInfo', bot.reply('Treatment options for this photo'))

    def test_new_concern_phrases_are_distinct_from_requests_for_another_photo(self):
        for text in ['new skin concern', 'I have another rash', 'I noticed a different skin problem']:
            self.assertEqual(make_bot().reply(text)['intent'], 'new_concern', text)
        self.assertEqual(make_bot().reply('Can I send another photo?')['intent'], 'image_request')

    def test_new_concern_preserves_text_only_preference_and_supplied_details(self):
        bot = make_bot()
        bot.reply('text only please')
        bot.reply('I have a new rash on my arm for three days')
        self.assertTrue(bot.conversation.get('image_declined'))
        self.assertIn('three days', bot.conversation.get('duration'))
        self.assertIn('arm', bot.conversation.get('location'))

    def test_warning_signs_in_a_new_concern_keep_priority(self):
        bot = make_bot()
        result = bot.reply('I have a new rash and I cannot breathe')
        self.assertEqual(result['intent'], 'emergency')

    def test_pure_symptom_denials_are_recorded_separately(self):
        for text in ['I have no rash or itching', 'no redness', 'my rash is not present', 'I do not have dry skin']:
            with self.subTest(text=text):
                bot = make_bot()
                with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
                    result = bot.reply(text)
                self.assertEqual(result['intent'], 'symptom_denial')
                self.assertEqual(bot.conversation.get('symptoms'), [])
                self.assertEqual(bot.conversation.get('denied_symptoms'), [text])
                self.assertFalse(bot.conversation.get('screening_paused'))
                self.assertIn("Symptoms you've denied", bot.reply('summarize our conversation')['reply'])

    def test_mixed_report_keeps_affirmative_symptoms(self):
        self.assertEqual(symptom_mentions('I have no rash, but my skin is dry'), ({'dry'}, {'rash'}))
        self.assertEqual(symptom_mentions('My rash is not itchy'), ({'rash'}, {'itchy'}))
        for text in ['I have no rash, but my skin is dry', 'My rash is not itchy']:
            bot = make_bot()
            self.assertEqual(bot.reply(text)['intent'], 'symptom')
            self.assertEqual(bot.conversation.get('symptoms'), [text])

    def test_medication_report_is_not_lost_when_it_mentions_absent_symptoms(self):
        bot = make_bot()
        result = bot.reply('I used a cream and I have no rash')
        self.assertEqual(result['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), 'I used a cream and I have no rash')
        self.assertEqual(bot.conversation.get('symptoms'), [])

    def test_denials_survive_restore_and_do_not_require_a_condition(self):
        bot = make_bot()
        bot.reply('no itching')
        restored = make_bot()
        restored.conversation.restore(bot.conversation.data)
        self.assertEqual(restored.conversation.get('denied_symptoms'), ['no itching'])
        self.assertIsNone(restored.conversation.get('classification'))
        restored.reply('new skin concern')
        self.assertEqual(restored.conversation.get('denied_symptoms'), [])

    def test_symptom_denial_does_not_bypass_actual_warning_signs(self):
        result = make_bot().reply('I have no rash but my lips are swollen')
        self.assertEqual(result['intent'], 'emergency')

    def test_new_concern_keeps_previous_messages_and_photos_in_history(self):
        app = create_app(make_bot(), history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        upload = client.post('/predict', data={'image': (io.BytesIO(PNG), 'skin.png')}).get_json()
        client.post('/predict', json={'message': 'I have a new rash on my leg'})
        history = client.get('/api/conversations/default').get_json()
        self.assertEqual(len(history['messages']), 4)
        self.assertEqual(history['messages'][1]['treatmentInfo']['condition_key'], 'atopic_dermatitis')
        self.assertEqual(client.get(upload['messages'][0]['image']).data, PNG)
        followup = client.post('/predict', json={'message': 'Treatment options for this photo'}).get_json()
        self.assertNotIn('treatmentInfo', followup)


if __name__ == '__main__':
    unittest.main()
