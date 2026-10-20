"""Regression checks for warnings, privacy, failed photos, and request isolation."""

import base64
import contextlib
import io
import os
import json
from pathlib import Path
import tempfile
from queue import Queue
from threading import Event, Thread
import unittest
from unittest.mock import patch

from app import create_app
from model.config import PROJECT_DIR, intent_model_path
from model.image_classifier import ImageClassifierError
from model.request_locks import OwnerLocks
from model.safety import safety_intent
from test_image_integration import make_bot


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class SafetyTests(unittest.TestCase):
    def test_current_emergencies_override_ordinary_model_guesses(self):
        for message in [
            'I cannot breathe', 'I am not able to breathe', 'My lips are swollen',
            'My tongue is swollen and I cannot swallow',
            'my tongue is getting bigger and swallowing is becoming difficult',
            'No fever, but my throat is swelling', 'I cannot breathe but I have no rash',
            'Can you help? My throat is swelling', 'My child cannot swallow',
            "I'm not sure if I'm having difficulty breathing",
        ]:
            with self.subTest(message=message):
                self.assertEqual(safety_intent(message, 'location'), 'emergency')

    def test_rash_warning_signs_get_medical_attention(self):
        for message in [
            'I have a rash and fever',
            'My rash is spreading rapidly and my skin is blistering',
            'My skin is peeling and my mouth has sores',
            'I have pus and yellow crusts on my rash', 'My rash is very painful',
            'I have a rash over most of my body', 'My skin has open sores',
            'I have no trouble breathing but my rash has pus',
        ]:
            with self.subTest(message=message):
                self.assertEqual(safety_intent(message, 'symptom'), 'medical_attention')

    def test_negated_or_educational_emergencies_do_not_claim_current_emergency(self):
        for message in [
            'I am not having trouble breathing', 'I do not have difficulty swallowing',
            'My lips are not swollen', 'My breathing is not difficult',
            'I am breathing normally',
            'No shortness of breath or throat swelling',
            'Can you explain trouble breathing as a symptom?', 'What is throat swelling?',
            'If I develop trouble breathing what should I do?',
            'What if I develop trouble breathing?',
        ]:
            with self.subTest(message=message):
                self.assertEqual(safety_intent(message, 'emergency'), 'safety_information')

    def test_negated_skin_warning_signs_do_not_trigger_medical_attention(self):
        for message in [
            'My rash is itchy', 'My rash is mild and I have no pus',
            'I have a rash but no fever or blisters', 'My rash is not painful',
            'My skin is dry, my mouth has no sores',
        ]:
            with self.subTest(message=message):
                self.assertIsNone(safety_intent(message, 'symptom'))

    def test_affirmative_warning_in_next_clause_survives_negation(self):
        for message, intent in [
            ('I have no fever and my skin is blistering', 'medical_attention'),
            ('My rash is not bad and I cannot breathe', 'emergency'),
        ]:
            self.assertEqual(safety_intent(message, 'symptom'), intent)

    def test_warning_endpoint_works_before_model_initialization(self):
        app = create_app(history_path=':memory:')
        app.config['TESTING'] = True
        self.addCleanup(app.extensions['chat_history'].db.close)
        with patch('builtins.__import__', wraps=__import__) as imports:
            result = app.test_client().post('/predict', json={'message': 'I cannot breathe'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json()['intent'], 'emergency')
        self.assertFalse(any(call.args[0] == 'model.semantic_chatbot' for call in imports.call_args_list))

    def test_warning_reply_does_not_need_text_inference_or_photo_classification(self):
        bot = make_bot()
        with patch.object(bot.classifier, 'predict', side_effect=AssertionError('Text inference must not run')):
            result = bot.reply('My rash is blistering', image=object())
        self.assertEqual(result['intent'], 'medical_attention')
        self.assertEqual(result['followUps'], [])
        self.assertIsNone(result['action'])
        self.assertTrue(bot.conversation.get('screening_paused'))
        self.assertEqual(bot.image_classifier.calls, 0)
        self.assertIsNone(bot.conversation.get('classification'))

    def test_model_emergency_guess_asks_about_warning_signs(self):
        bot = make_bot()
        with patch.object(bot.classifier, 'predict', return_value=('emergency', .8)):
            result = bot.reply('Something frightening is happening')
        self.assertEqual(result['intent'], 'safety_check')
        self.assertIn('If yes', result['reply'])
        self.assertFalse(bot.conversation.get('screening_paused'))


class PhotoAndPrivacyTests(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.app = create_app(self.bot)
        self.app.config['TESTING'] = True
        self.addCleanup(self.app.extensions['chat_history'].db.close)
        self.client = self.app.test_client()

    def upload(self):
        return self.client.post('/predict', data={'image': (io.BytesIO(PNG), 'skin.png')})

    def test_service_failure_invalidates_previous_photo_and_persists_the_failure(self):
        accepted = self.upload().get_json()
        with patch.object(self.bot.image_classifier, 'predict', side_effect=ImageClassifierError('offline')):
            failed = self.upload()
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.get_json()['intent'], 'image_error')
        for message in ['What do you think about the latest photo?', 'Explain simply', 'How can I treat it?']:
            result = self.client.post('/predict', json={'message': message}).get_json()
            self.assertIn("couldn't reliably classify", result['reply'])
            self.assertNotIn('88.0%', result['reply'])
            self.assertNotIn('sourceImageId', result)
        state = self.app.extensions['chat_history'].get(
            self.owner(), 'default'
        )['state']
        self.assertIsNone(json.loads(state)['classification'])
        restored = make_bot()
        restored.conversation.restore(json.loads(state))
        self.assertIn("couldn't reliably classify", restored.reply('What does this result mean?')['reply'])
        detail = self.client.get('/api/conversations/default').get_json()
        self.assertEqual(detail['messages'][1]['sourceImageId'], accepted['messages'][0]['id'])
        self.assertEqual(self.client.get(accepted['messages'][0]['image']).data, PNG)

    def owner(self):
        with self.client.session_transaction() as session:
            return session['client_id']

    def test_photo_explanations_reference_the_correct_saved_attachment(self):
        first = self.upload().get_json()
        second = self.upload().get_json()
        result = self.client.post('/predict', json={'message': 'What does this result mean?'}).get_json()
        self.assertEqual(result['sourceImageId'], second['messages'][0]['id'])
        self.assertNotEqual(result['sourceImageId'], first['messages'][0]['id'])

    def test_sensitive_messages_and_state_are_not_printed(self):
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
            self.client.post('/predict', json={'message': 'My private rash is itchy on my arm'})
            self.client.post('/predict', json={'message': 'Summarize our conversation'})
        self.assertEqual(captured.getvalue(), '')

    def test_normal_skin_response_does_not_clear_the_patient(self):
        self.bot.image_classifier.result.update(predicted_class='normal_skin', condition='Normal Skin')
        result = self.upload().get_json()
        self.assertIn('does not confirm healthy skin', result['reply'])


class RequestIsolationTests(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.app = create_app(self.bot)
        self.app.config['TESTING'] = True
        self.addCleanup(self.app.extensions['chat_history'].db.close)
        self.client = self.app.test_client()
        self.client.get('/api/conversations')
        self.entered, self.release = Event(), Event()
        self.results = Queue()
        self.workers = []
        original = self.bot.image_classifier.predict

        def slow(image):
            self.entered.set()
            if not self.release.wait(5):
                raise RuntimeError('Test did not release image inference')
            return original(image)

        mock = patch.object(self.bot.image_classifier, 'predict', side_effect=slow)
        mock.start()
        self.addCleanup(mock.stop)
        self.addCleanup(self.finish_workers)

    def finish_workers(self):
        self.release.set()
        for worker in self.workers:
            worker.join(5)

    def background(self, action):
        done = Event()

        def run():
            try:
                self.results.put(action())
            except Exception as error:
                self.results.put(error)
            finally:
                done.set()

        worker = Thread(target=run)
        self.workers.append(worker)
        worker.start()
        return done

    def start_upload(self):
        sender = self.app.test_client()
        sender.set_cookie('session', self.client.get_cookie('session').value)
        done = self.background(lambda: sender.post('/predict', data={
            'conversation_id': 'slow', 'image': (io.BytesIO(PNG), 'skin.png'),
        }))
        self.assertTrue(self.entered.wait(3))
        return done

    def test_other_browsers_can_chat_and_history_remains_readable_during_upload(self):
        pending = self.start_upload()
        other = self.app.test_client()
        chat_done = self.background(lambda: other.post('/predict', json={'message': 'my skin is itchy'}))
        reader = self.app.test_client()
        reader.set_cookie('session', self.client.get_cookie('session').value)
        history_done = self.background(lambda: reader.get('/api/conversations'))
        self.assertTrue(chat_done.wait(2), 'Another browser was blocked by image inference')
        self.assertTrue(history_done.wait(2), 'History was blocked by image inference')
        self.assertFalse(pending.is_set())
        self.finish_workers()
        for _ in range(3):
            response = self.results.get(timeout=1)
            self.assertFalse(isinstance(response, Exception), repr(response))
            self.assertEqual(response.status_code, 200)

    def test_clear_history_waits_for_own_upload_then_removes_it(self):
        self.start_upload()
        deleter = self.app.test_client()
        deleter.set_cookie('session', self.client.get_cookie('session').value)
        deletion = self.background(lambda: deleter.delete('/api/conversations'))
        self.assertFalse(deletion.wait(.15))
        self.release.set()
        self.assertTrue(deletion.wait(3))
        self.finish_workers()
        self.assertEqual(self.client.get('/api/conversations').get_json()['conversations'], [])
        self.assertEqual(self.client.get('/api/conversations/slow').status_code, 404)

    def test_owner_lock_registry_releases_entries_after_success_and_error(self):
        locks = OwnerLocks()
        with locks.hold('one'):
            with locks.hold('one'):
                self.assertEqual(len(locks._registry), 1)
        self.assertEqual(locks._registry, {})
        with self.assertRaises(RuntimeError), locks.hold('one'):
            raise RuntimeError('fixture')
        self.assertEqual(locks._registry, {})


class ModelConfigurationTests(unittest.TestCase):
    def test_default_and_override_are_resolved_independently_of_working_directory(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True), patch('model.config.ACTIVE_MODEL_MANIFEST', Path(directory) / 'absent.json'):
            self.assertEqual(intent_model_path(), PROJECT_DIR / 'semantic_classifier.pkl')
        with patch.dict(os.environ, {'FLAMMA_INTENT_MODEL': 'semantic_classifier_balanced_v2.pkl'}):
            self.assertEqual(intent_model_path(), PROJECT_DIR / 'semantic_classifier_balanced_v2.pkl')
        absolute = PROJECT_DIR / 'semantic_classifier.pkl'
        with patch.dict(os.environ, {'FLAMMA_INTENT_MODEL': str(absolute)}):
            self.assertEqual(intent_model_path(), absolute)


class LegacyPhotoHistoryTests(unittest.TestCase):
    def test_old_failed_upload_state_is_repaired_when_history_is_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.sqlite3'
            old_app = create_app(make_bot(), history_path=path)
            new_app = None
            try:
                client = old_app.test_client()
                client.post('/predict', data={'image': (io.BytesIO(PNG), 'old.png')})
                with client.session_transaction() as session:
                    owner = session['client_id']
                history = old_app.extensions['chat_history']
                stale_state = json.loads(history.get(owner, 'default')['state'])
                self.assertIsNotNone(stale_state['classification'])
                history.save_turn(owner, 'default', '', dict(
                    reply='The image service was unavailable.', intent='image_error',
                    confidence=None, followUps=[],
                ), stale_state, PNG, 'image/png')
                new_app = create_app(make_bot(), history_path=path)
                new_client = new_app.test_client()
                new_client.set_cookie('session', client.get_cookie('session').value)
                result = new_client.post('/predict', json={'message': 'What does this result mean?'}).get_json()
                self.assertIn("couldn't reliably classify", result['reply'])
                self.assertNotIn('88.0%', result['reply'])
                self.assertEqual(new_client.get('/api/conversations/default').get_json()['messages'][1]['imageResult']['status'], 'ok')
                new_client.post('/predict', json={'message': 'What is psoriasis?'})
                third_app = create_app(make_bot(), history_path=path)
                try:
                    third_client = third_app.test_client()
                    third_client.set_cookie('session', new_client.get_cookie('session').value)
                    explicit = third_client.post('/predict', json={'message': 'And treatment?'}).get_json()
                    self.assertIn('General information about Psoriasis', explicit['reply'])
                    self.assertNotIn("couldn't reliably classify", explicit['reply'])
                finally:
                    third_app.extensions['chat_history'].db.close()
            finally:
                if new_app:
                    new_app.extensions['chat_history'].db.close()
                old_app.extensions['chat_history'].db.close()


if __name__ == '__main__':
    unittest.main()
