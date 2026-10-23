"""Quick replies follow the actual answer, survive history, and keep their actions."""

import json
import unittest
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from app import create_app
from model.image_classifier import ImageClassifierError
from model.reply_choices import with_reply_choices
from test_image_integration import make_bot


class ReplyChoiceTests(unittest.TestCase):
    def assert_choices(self, result):
        choices = result['followUps']
        self.assertGreaterEqual(len(choices), 3, result)
        self.assertEqual(len(choices), len({choice.lower() for choice in choices}))
        self.assertTrue(all(isinstance(choice, str) and choice == choice.strip() and choice for choice in choices))

    def app_client(self, bot=None):
        app = create_app(bot or make_bot())
        app.config['TESTING'] = True
        self.addCleanup(app.extensions['chat_history'].db.close)
        return app, app.test_client()

    def test_choices_answer_the_next_question_rather_than_the_previous_intent(self):
        bot = make_bot()
        for text, expected in [
            ('hello', 'I have a rash'), ('I have a rash', 'My arm'),
            ('My arm', 'Two weeks'), ('Two weeks', 'None'),
            ('None', 'Choose photo'),
        ]:
            with self.subTest(text=text):
                result = bot.reply(text)
                self.assert_choices(result)
                self.assertIn(expected, result['followUps'])
        self.assertIsNone(bot.conversation.get('severity'))

    def test_photo_request_has_one_explicit_picker_action_and_text_alternatives(self):
        bot = make_bot()
        result = bot.reply('can i upload a photo?')
        self.assert_choices(result)
        self.assertEqual(result['followUps'].count('Choose photo'), 1)
        self.assertEqual(result['action'], 'upload_image')
        self.assertIn('Text only', result['followUps'])
        self.assertEqual(bot.image_classifier.calls, 0)
        followup = bot.reply('Text only')
        self.assert_choices(followup)
        self.assertNotEqual(followup.get('action'), 'upload_image')

    def test_information_choices_name_the_condition_and_offer_a_new_topic(self):
        bot = make_bot()
        result = bot.reply('What causes psoriasis?')
        self.assert_choices(result)
        self.assertIn('What are the symptoms of Psoriasis?', result['followUps'])
        self.assertIn('Explain simply', result['followUps'])
        followup = bot.reply('What are the symptoms of Psoriasis?')
        self.assertIn(bot.knowledge.get('psoriasis', 'symptoms'), followup['reply'])

    def test_short_clarification_keeps_the_real_choices_and_adds_a_supported_action(self):
        bot = make_bot()
        result = bot.reply('Could it be eczema or psoriasis?')
        self.assert_choices(result)
        self.assertEqual(result['followUps'][:2], ['Dermatitis', 'Psoriasis'])
        self.assertEqual(bot.reply(result['followUps'][2])['intent'], 'conversation_summary')
        self.assertIsNone(bot.conversation.get('classification'))

    def test_optional_severity_choices_follow_its_field_and_never_assign_a_grade(self):
        bot = make_bot()
        result = bot.reply('How severe is my psoriasis?')
        self.assert_choices(result)
        self.assertIn('My arms', result['followUps'])
        result = bot.reply('My arms')
        self.assert_choices(result)
        self.assertIn('About one handprint', result['followUps'])
        self.assertIsNone(bot.conversation.get('severity'))
        self.assertFalse({'Mild', 'Moderate', 'Severe'} & set(result['followUps']))

    def test_warning_choices_preserve_the_warning_and_do_not_request_an_upload(self):
        bot = make_bot()
        with patch.object(bot.classifier, 'predict', side_effect=AssertionError('No text model needed')):
            result = bot.reply('I cannot breathe')
        self.assert_choices(result)
        self.assertEqual(result['intent'], 'emergency')
        self.assertIn('seek emergency medical care now', result['reply'])
        self.assertIn('When should I see a doctor?', result['followUps'])
        self.assertNotIn('Choose photo', result['followUps'])
        self.assertNotIn('Continue screening', result['followUps'])
        self.assertIsNone(result.get('action'))

    def test_successful_rejected_and_unavailable_photos_all_have_relevant_choices(self):
        for status in ['ok', 'rejected', 'unavailable']:
            with self.subTest(status=status):
                bot = make_bot()
                if status == 'rejected':
                    bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
                if status == 'unavailable':
                    bot.image_classifier.predict = lambda image: (_ for _ in ()).throw(ImageClassifierError())
                result = bot.reply('', FileStorage(filename='fixture.png'))
                self.assert_choices(result)
                self.assertIn('Can I send another picture?', result['followUps'])
                if status != 'ok':
                    self.assertIn('Text only', result['followUps'])
                    self.assertIsNone(bot.conversation.get('classification'))

    def test_history_and_retry_keep_the_same_choices_without_duplicate_messages(self):
        app, client = self.app_client()
        payload = {'message': 'hello', 'conversation_id': 'choices', 'request_id': 'one'}
        first = client.post('/predict', json=payload).get_json()
        retry = client.post('/predict', json=payload).get_json()
        detail = client.get('/api/conversations/choices').get_json()
        self.assert_choices(first)
        self.assertEqual(first['followUps'], retry['followUps'])
        self.assertEqual(detail['messages'], first['messages'])
        self.assertEqual(len(detail['messages']), 2)
        self.assertEqual(detail['messages'][1]['followUps'], first['followUps'])
        self.assertNotIn('followUps', detail['messages'][0])

    def test_old_history_gets_choices_without_rewriting_its_saved_text_or_payload(self):
        app, client = self.app_client()
        client.post('/predict', json={'message': 'hello', 'conversation_id': 'old'})
        history = app.extensions['chat_history']
        row = history.db.execute("SELECT id, payload FROM messages WHERE json_extract(payload, '$.who')='bot'").fetchone()
        original = json.loads(row['payload'])
        original.pop('choiceContext', None)
        original['followUps'] = []
        original['text'] = 'Where is the affected area located?'
        stored = json.dumps(original)
        history.db.execute('UPDATE messages SET payload=? WHERE id=?', (stored, row['id']))
        history.db.commit()
        served = client.get('/api/conversations/old').get_json()['messages'][-1]
        self.assert_choices(served)
        self.assertEqual(served['followUps'], ['My arm', 'My face', "I'm not sure"])
        self.assertEqual(served['text'], original['text'])
        self.assertEqual(history.db.execute('SELECT payload FROM messages WHERE id=?', (row['id'],)).fetchone()['payload'], stored)

    def test_validation_replies_have_choices_and_keep_their_http_status(self):
        app, client = self.app_client()
        for payload in [[], {'message': 12}, {'message': ''}]:
            with self.subTest(payload=payload):
                response = client.post('/predict', json=payload)
                self.assertIn(response.status_code, [200, 400])
                self.assert_choices(response.get_json())
        app.config['MAX_CONTENT_LENGTH'] = 2
        response = client.post('/predict', json={'message': 'too large'})
        self.assertEqual(response.status_code, 413)
        self.assert_choices(response.get_json())

    def test_duplicate_invalid_and_existing_choices_are_handled_without_losing_curated_options(self):
        result = with_reply_choices({'intent': 'greeting', 'followUps': [' Rash ', 'rash', None, 12, '', 'Upload a photo']})
        self.assert_choices(result)
        self.assertEqual(result['followUps'][:2], ['Rash', 'Upload a photo'])
        numeric = with_reply_choices({'intent': 'invalid_duration', 'followUps': ['2 days', '2 weeks', '2 months']})
        self.assertEqual(numeric['followUps'], ['2 days', '2 weeks', '2 months'])


if __name__ == '__main__':
    unittest.main()
