"""Run with: python -B -m unittest test_chat_history."""

import base64
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from app import create_app
from test_image_integration import make_bot

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=')


class HistoryTests(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'history.sqlite3'
        self.app = self.make_app()
        self.client = self.app.test_client()

    def make_app(self):
        app = create_app(make_bot(), history_path=self.path)
        app.config['TESTING'] = True
        self.addCleanup(app.extensions['chat_history'].db.close)
        return app

    def send(self, message='my skin is itchy', chat='one', client=None):
        response = (client or self.client).post('/predict', json={'message': message, 'conversation_id': chat})
        self.assertEqual(response.status_code, 200)
        return response.get_json()

    def restart_client(self):
        client = self.make_app().test_client()
        client.set_cookie('session', self.client.get_cookie('session').value)
        return client

    def upload(self):
        return self.client.post('/predict', data={
            'conversation_id': 'one', 'image': (io.BytesIO(PNG), 'skin.png'),
        }).get_json()

    def test_saved_exchange_has_stable_ids_dates_and_searchable_text(self):
        sent = self.send()
        detail = self.client.get('/api/conversations/one').get_json()
        self.assertEqual(detail['messages'], sent['messages'])
        self.assertEqual([m['who'] for m in detail['messages']], ['user', 'bot'])
        self.assertTrue(all(m['createdAt'] for m in detail['messages']))
        result = self.client.get('/api/conversations?q=affected%20area').get_json()['conversations']
        self.assertEqual(result[0]['id'], 'one')
        self.assertIn('affected area', result[0]['match'])

    def test_restart_restores_history_and_screening_context(self):
        self.send()
        self.send('in my arms')
        restarted = self.restart_client()
        self.assertEqual(len(restarted.get('/api/conversations/one').get_json()['messages']), 4)
        result = self.send('two weeks', client=restarted)
        self.assertEqual(result['intent'], 'duration')
        self.assertIn('medication', result['reply'])
        self.assertEqual(len(restarted.get('/api/conversations/one').get_json()['messages']), 6)

    def test_restart_remembers_the_last_topic_and_actual_pending_question(self):
        self.upload()
        self.send('how can i treat it?')
        restarted = self.restart_client()
        unsure = self.send('idk', client=restarted)
        self.assertIn('shorter explanation', unsure['reply'])
        self.assertNotIn('marked duration', unsure['reply'])
        simpler = self.send('explain simply', client=restarted)
        self.assertIn('Short version', simpler['reply'])
        summary = self.send('summarize our conversation', client=restarted)
        self.assertIn('Skin symptoms: not provided', summary['reply'])
        self.assertIn('How long: not provided', summary['reply'])
        self.assertIn('Atopic Dermatitis', summary['reply'])
        result = self.send('continue screening', client=restarted)
        self.assertIn('Can you describe', result['reply'])

    def test_paused_screening_survives_restart_and_resumes_the_missing_field(self):
        self.send('my rash is itchy')
        self.send('skip the questions')
        restarted = self.restart_client()
        result = self.send('my arm', client=restarted)
        self.assertNotIn('How long', result['reply'])
        result = self.send('continue screening', client=restarted)
        self.assertIn('How long', result['reply'])

    def test_restart_keeps_the_exact_dermatitis_subtype_for_disease_questions(self):
        self.upload()
        restarted = self.restart_client()
        result = self.send('what is this disease?', client=restarted)
        self.assertIn('General information about Atopic Dermatitis', result['reply'])
        self.assertIn('not a confirmed diagnosis', result['reply'])
        result = self.send('what is contact dermatitis?', client=restarted)
        self.assertIn('General information about Contact Dermatitis', result['reply'])
        result = self.send('what is this disease?', client=self.restart_client())
        self.assertIn('General information about Contact Dermatitis', result['reply'])

    def test_summary_cannot_leak_into_a_new_conversation_or_another_owner(self):
        self.upload()
        self.send('my rash is itchy')
        own = self.send('summarize our conversation')
        self.assertIn('Atopic Dermatitis', own['reply'])
        for chat, client in [('new-chat', self.client), ('one', self.app.test_client())]:
            result = self.send('summarize our conversation', chat=chat, client=client)
            self.assertIn('Skin symptoms: not provided', result['reply'])
            self.assertNotIn('Atopic Dermatitis', result['reply'])

    def test_restart_restores_photo_results_attachment_and_disease_context(self):
        sent = self.upload()
        url = sent['messages'][0]['image']
        restarted = self.restart_client()
        photo = restarted.get(url)
        self.assertEqual(photo.data, PNG)
        self.assertEqual(photo.mimetype, 'image/png')
        self.assertEqual(photo.headers['Cache-Control'], 'no-store')
        detail = restarted.get('/api/conversations/one').get_json()
        self.assertEqual(detail['messages'][1]['imageResult'], sent['imageResult'])
        self.assertNotIn('Which of these conditions', self.send('what is it?', client=restarted)['reply'])

    def test_owner_isolation_for_list_search_read_rename_delete_and_photos(self):
        sent = self.upload()
        other = self.app.test_client()
        self.assertEqual(other.get('/api/conversations?q=dermatitis').get_json()['conversations'], [])
        for method in ['get', 'delete']:
            self.assertEqual(getattr(other, method)('/api/conversations/one').status_code, 404)
        self.assertEqual(other.patch('/api/conversations/one', json={'title': 'Stolen'}).status_code, 404)
        self.assertEqual(other.get(sent['messages'][0]['image']).status_code, 404)
        other.delete('/api/conversations')
        self.assertEqual(self.client.get('/api/conversations/one').status_code, 200)

    def test_rename_survives_followup_and_is_searchable(self):
        self.send()
        renamed = self.client.patch('/api/conversations/one', json={'title': '  Arm check  '}).get_json()
        self.assertEqual(renamed['conversation']['title'], 'Arm check')
        self.send('in my arms')
        result = self.client.get('/api/conversations?q=ARM%20CHECK').get_json()['conversations']
        self.assertEqual(result[0]['title'], 'Arm check')

    def test_rename_validation(self):
        self.send()
        for title in ['', '   ', 'x' * 101, None, 123, []]:
            with self.subTest(title=title):
                self.assertEqual(self.client.patch('/api/conversations/one', json={'title': title}).status_code, 400)
        self.assertEqual(self.client.patch('/api/conversations/one', json=[]).status_code, 400)

    def test_literal_search_wildcards_and_empty_search(self):
        self.send()
        for term in ['%', '_', "' OR 1=1 --", '\\']:
            with self.subTest(term=term):
                self.assertEqual(self.client.get('/api/conversations', query_string={'q': term}).get_json()['conversations'], [])
        self.assertEqual(len(self.client.get('/api/conversations?q=').get_json()['conversations']), 1)

    def test_delete_removes_messages_images_and_cached_state(self):
        sent = self.upload()
        self.send(chat='two')
        self.assertEqual(self.client.delete('/api/conversations/one').status_code, 200)
        self.assertEqual(self.client.get('/api/conversations/one').status_code, 404)
        self.assertEqual(self.client.get(sent['messages'][0]['image']).status_code, 404)
        self.assertEqual(len(self.client.get('/api/conversations').get_json()['conversations']), 1)
        self.assertIn('Which of these conditions', self.send('what is it?')['reply'])

    def test_clear_history_removes_all_owned_chats_and_leaves_other_browser(self):
        self.upload()
        self.send(chat='two')
        other = self.app.test_client()
        self.send(client=other)
        self.client.delete('/api/conversations')
        self.assertEqual(self.client.get('/api/conversations').get_json()['conversations'], [])
        self.assertEqual(len(other.get('/api/conversations').get_json()['conversations']), 1)
        self.assertIn('Which of these conditions', self.send('what is it?')['reply'])

    def test_untrusted_attachment_is_not_served_as_an_image(self):
        result = self.client.post('/predict', data={
            'image': (io.BytesIO(b'<script>alert(1)</script>'), 'skin.png'),
        }).get_json()
        self.assertNotIn('image', result['messages'][0])

    def test_photo_followups_and_unknown_symptoms_survive_restart(self):
        self.upload()
        self.send('i dont know')
        restarted = self.restart_client()
        result = self.send('i mean what is your thoiughts about it', client=restarted)
        self.assertEqual(result['intent'], 'image_explanation')
        self.assertIn('Atopic Dermatitis', result['reply'])
        result = self.send('my arm', client=restarted)
        self.assertEqual(result['intent'], 'location')
        self.assertIn('How long', result['reply'])

    def test_restore_rechecks_an_invalid_location_from_older_versions(self):
        self.upload()
        store = self.app.extensions['chat_history']
        with self.client.session_transaction() as session:
            owner = session['client_id']
        import json
        state = json.loads(store.get(owner, 'one')['state'])
        state['location'] = 'dssd'
        with store.db:
            store.db.execute('UPDATE conversations SET state=? WHERE owner=? AND id=?', (json.dumps(state), owner, 'one'))
        restarted = self.restart_client()
        result = self.send('i dont know', client=restarted)
        self.assertIn('Where', result['reply'])
        result = self.send('my arm', client=restarted)
        self.assertIn('How long', result['reply'])

    def test_resume_discards_bad_location_and_shorthand_duration_without_erasing_messages(self):
        self.send('hello')
        self.send('banana')
        self.send('lala mo')
        store = self.app.extensions['chat_history']
        with self.client.session_transaction() as session:
            owner = session['client_id']
        import json
        state = json.loads(store.get(owner, 'one')['state'])
        state.update(location='banana', duration='lala mo')
        with store.db:
            store.db.execute('UPDATE conversations SET state=? WHERE owner=? AND id=?', (json.dumps(state), owner, 'one'))
        restarted = self.restart_client()
        result = self.send('summarize our conversation', client=restarted)
        self.assertIn('Affected area: not provided', result['reply'])
        self.assertIn('How long: not provided', result['reply'])
        messages = restarted.get('/api/conversations/one').get_json()['messages']
        self.assertIn('banana', [message['text'] for message in messages])
        self.assertIn('lala mo', [message['text'] for message in messages])


if __name__ == '__main__':
    unittest.main()
