"""Durable retry receipts must not repeat inference, facts, or saved exchanges."""

import io
from pathlib import Path
from queue import Queue
from threading import Event, Thread
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from model.errors import TextModelUnavailable
from model.image_classifier import ImageClassifierError
from test_image_integration import make_bot
from test_safety_and_reliability import PNG


class RequestReceiptTests(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()
        self.app = create_app(self.bot)
        self.addCleanup(self.app.extensions['chat_history'].db.close)
        self.client = self.app.test_client()
        self.client.get('/api/conversations')

    def send(self, message='my skin is itchy', request_id='attempt-1', chat_id='default', client=None):
        return (client or self.client).post('/predict', json={
            'message': message, 'request_id': request_id, 'conversation_id': chat_id})

    def upload(self, request_id='photo-1', content=PNG, filename='skin.png', client=None):
        return (client or self.client).post('/predict', data={
            'request_id': request_id, 'image': (io.BytesIO(content), filename)})

    def test_repeated_text_request_returns_same_saved_exchange_without_inference(self):
        with patch.object(self.bot.classifier, 'predict', wraps=self.bot.classifier.predict) as predict:
            first, replay = self.send().get_json(), self.send().get_json()
        self.assertEqual(predict.call_count, 1)
        self.assertTrue(replay['replayed'])
        self.assertEqual(first['messages'], replay['messages'])
        self.assertEqual(first['reply'], replay['reply'])
        self.assertEqual(replay['requestId'], 'attempt-1')
        self.assertEqual(len(self.client.get('/api/conversations/default').get_json()['messages']), 2)

    def test_retry_after_later_turn_does_not_roll_back_current_state(self):
        self.send('my rash is itchy on my arm for two weeks')
        self.send('I used a cream', request_id='attempt-2')
        self.send('my rash is itchy on my arm for two weeks')
        with self.client.session_transaction() as session:
            owner = session['client_id']
        import json
        state = json.loads(self.app.extensions['chat_history'].get(owner, 'default')['state'])
        self.assertEqual(state['medication'], 'I used a cream')
        self.assertEqual(len(self.client.get('/api/conversations/default').get_json()['messages']), 4)

    def test_same_id_with_changed_text_is_rejected_without_saving(self):
        self.send()
        conflict = self.send('my skin is dry')
        self.assertEqual(conflict.status_code, 409)
        self.assertNotIn('messages', conflict.get_json())
        self.assertEqual(len(self.client.get('/api/conversations/default').get_json()['messages']), 2)

    def test_identical_photos_are_not_classified_twice_and_keep_treatment_source(self):
        first, replay = self.upload().get_json(), self.upload().get_json()
        self.assertEqual(self.bot.image_classifier.calls, 1)
        self.assertEqual(first['messages'], replay['messages'])
        self.assertEqual(replay['messages'][1]['sourceImageId'], first['messages'][0]['id'])
        self.assertEqual(replay['treatmentInfo']['condition_key'], 'atopic_dermatitis')

    def test_changed_photo_bytes_or_filename_cannot_reuse_id(self):
        self.upload()
        self.assertEqual(self.upload(content=PNG + b'different').status_code, 409)
        self.assertEqual(self.upload(filename='another.png').status_code, 409)
        self.assertEqual(self.bot.image_classifier.calls, 1)

    def test_invalid_image_bytes_still_contribute_to_fingerprint(self):
        self.upload(content=b'first invalid content')
        self.assertEqual(self.upload(content=b'different invalid content').status_code, 409)

    def test_saved_image_errors_replay_the_original_status(self):
        with patch.object(self.bot.image_classifier, 'predict', side_effect=ImageClassifierError('offline')) as predict:
            first, replay = self.upload(), self.upload()
        self.assertEqual(predict.call_count, 1)
        self.assertEqual(first.status_code, 503)
        self.assertEqual(replay.status_code, 503)
        self.assertTrue(replay.get_json()['replayed'])
        self.assertEqual(first.get_json()['messages'], replay.get_json()['messages'])

    def test_request_keys_are_scoped_to_browser_and_conversation(self):
        other = self.app.test_client()
        self.send(client=other)
        self.send()
        self.send(chat_id='second')
        for client, chat_id in [(other, 'default'), (self.client, 'default'), (self.client, 'second')]:
            self.assertEqual(len(client.get('/api/conversations/' + chat_id).get_json()['messages']), 2)
        self.assertEqual(self.app.extensions['chat_history'].db.execute('SELECT COUNT(*) FROM request_receipts').fetchone()[0], 3)

    def test_invalid_request_ids_fail_before_text_inference(self):
        for request_id in ['', '../bad', ['array'], 123, 'x' * 65]:
            self.assertEqual(self.send(request_id=request_id).status_code, 400)

    def test_deleting_a_chat_cascades_its_receipts(self):
        self.send()
        self.client.delete('/api/conversations/default')
        self.assertEqual(self.app.extensions['chat_history'].db.execute('SELECT COUNT(*) FROM request_receipts').fetchone()[0], 0)

    def test_legacy_requests_without_ids_remain_supported(self):
        for _ in range(2):
            self.client.post('/predict', json={'message': 'my skin is itchy'})
        self.assertEqual(len(self.client.get('/api/conversations/default').get_json()['messages']), 4)

    def test_concurrent_identical_uploads_are_serialized_and_replayed(self):
        entered, release = Event(), Event()
        results = Queue()
        original = self.bot.image_classifier.predict
        def delayed(image):
            entered.set()
            if not release.wait(5):
                raise AssertionError('Test did not release image inference')
            return original(image)
        cookie = self.client.get_cookie('session').value
        def run():
            sender = self.app.test_client()
            sender.set_cookie('session', cookie)
            results.put(self.upload(client=sender))
        with patch.object(self.bot.image_classifier, 'predict', side_effect=delayed):
            first, second = Thread(target=run), Thread(target=run)
            first.start()
            try:
                self.assertTrue(entered.wait(3))
                second.start()
            finally:
                release.set()
                first.join(5)
                if second.ident is not None:
                    second.join(5)
        self.assertEqual(self.bot.image_classifier.calls, 1)
        replies = [results.get(timeout=2), results.get(timeout=2)]
        self.assertTrue(all(reply.status_code == 200 for reply in replies))
        self.assertEqual(replies[0].get_json()['messages'], replies[1].get_json()['messages'])

    def test_receipt_survives_server_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'history.sqlite'
            first_app = create_app(make_bot(), history_path=path)
            first_client = first_app.test_client()
            first = self.send(client=first_client).get_json()
            cookie = first_client.get_cookie('session').value
            first_app.extensions['chat_history'].db.close()
            second_bot = make_bot()
            second_app = create_app(second_bot, history_path=path)
            try:
                second_client = second_app.test_client()
                second_client.set_cookie('session', cookie)
                with patch.object(second_bot.classifier, 'predict', side_effect=AssertionError('Must use receipt')):
                    replay = self.send(client=second_client).get_json()
                self.assertEqual(first['messages'], replay['messages'])
            finally:
                second_app.extensions['chat_history'].db.close()

    def test_warning_receipt_does_not_need_a_model(self):
        app = create_app(history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        first = self.send('I cannot breathe', client=client).get_json()
        replay = self.send('I cannot breathe', client=client).get_json()
        self.assertEqual(first['messages'], replay['messages'])
        self.assertEqual(replay['intent'], 'emergency')
        self.assertEqual(client.get('/health').get_json()['chat_model'], 'not_loaded')

    def test_unsaved_model_failure_does_not_reserve_request_id(self):
        app = create_app(history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        with patch('model.semantic_chatbot.SemanticChatbot', side_effect=TextModelUnavailable('offline')):
            self.assertEqual(self.send(client=client).status_code, 503)
        with patch('model.semantic_chatbot.SemanticChatbot', return_value=make_bot()):
            self.assertEqual(self.send(client=client).status_code, 200)
        self.assertEqual(len(client.get('/api/conversations/default').get_json()['messages']), 2)


if __name__ == '__main__':
    unittest.main()
