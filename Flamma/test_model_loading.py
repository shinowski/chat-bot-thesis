"""Cached chat startup must not retry blocked network requests."""

import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
from threading import Event
import unittest
from unittest.mock import Mock, patch

from app import create_app
from model.errors import TextModelUnavailable
from test_image_integration import make_bot


class LocalModelTests(unittest.TestCase):
    def load_module(self, loader):
        dependency = ModuleType('sentence_transformers')
        dependency.SentenceTransformer = loader
        with patch.dict(sys.modules, {'sentence_transformers': dependency}):
            spec = importlib.util.spec_from_file_location('local_model_test', Path(__file__).parent / 'model/semantic_model.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module

    def test_cached_model_loads_when_remote_requests_are_forbidden(self):
        network = Mock(side_effect=AssertionError('A chat request must not use the network'))
        cached = SimpleNamespace(encode=Mock(return_value='fixture embeddings'))

        def loader(name, **options):
            if not options.get('local_files_only'):
                network()
            return cached

        model = self.load_module(loader).SemanticModel()
        self.assertEqual(model.encode(['hello']), 'fixture embeddings')
        network.assert_not_called()

    def test_missing_cache_fails_once_with_a_handled_error(self):
        loader = Mock(side_effect=OSError('Cache not installed'))
        module = self.load_module(loader)
        with self.assertRaises(TextModelUnavailable):
            module.SemanticModel()
        self.assertEqual(loader.call_count, 1)


class ModelStartupRouteTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(history_path=':memory:')
        self.app.config['TESTING'] = True
        self.addCleanup(self.app.extensions['chat_history'].db.close)

    def constructor(self, constructor):
        module = ModuleType('model.semantic_chatbot')
        module.SemanticChatbot = constructor
        return patch.dict(sys.modules, {'model.semantic_chatbot': module})

    def test_ordinary_messages_initialize_once_then_reuse_model(self):
        constructor = Mock(return_value=make_bot())
        with self.constructor(constructor):
            for _ in range(2):
                result = self.app.test_client().post('/predict', json={'message': 'My skin is itchy'})
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.get_json()['intent'], 'symptom')
        self.assertEqual(constructor.call_count, 1)
        self.assertEqual(self.app.test_client().get('/health').get_json()['chat_model'], 'ready')

    def test_background_startup_initializes_once_and_keeps_warnings_available(self):
        entered, release = Event(), Event()
        self.addCleanup(release.set)

        def load():
            entered.set()
            if not release.wait(5):
                raise AssertionError('Startup test did not release the loader')
            return make_bot()

        constructor = Mock(side_effect=load)
        with self.constructor(constructor):
            worker = self.app.extensions['warm_chat_model']()
            self.assertTrue(entered.wait(3))
            client = self.app.test_client()
            self.assertEqual(client.get('/health').get_json()['chat_model'], 'loading')
            self.assertEqual(client.post('/predict', json={'message': 'I cannot breathe'}).get_json()['intent'], 'emergency')
            self.assertEqual(client.get('/api/conversations').status_code, 200)
            release.set()
            worker.join(3)
            self.assertFalse(worker.is_alive())
            second = self.app.extensions['warm_chat_model']()
            second.join(3)
            self.assertEqual(client.post('/predict', json={'message': 'my skin is itchy'}).status_code, 200)
        self.assertEqual(constructor.call_count, 1)

    def test_background_cache_failure_is_handled_without_private_error_details(self):
        constructor = Mock(side_effect=TextModelUnavailable('Private loader exception'))
        with self.constructor(constructor), self.assertLogs(self.app.logger, level='WARNING') as logs:
            worker = self.app.extensions['warm_chat_model']()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        self.assertEqual(self.app.test_client().get('/health').get_json()['chat_model'], 'not_loaded')
        self.assertNotIn('Private loader exception', '\n'.join(logs.output))

    def test_missing_model_returns_retryable_error_and_warning_replies_still_work(self):
        constructor = Mock(side_effect=TextModelUnavailable('Sensitive internal exception detail'))
        client = self.app.test_client()
        with self.constructor(constructor), self.assertLogs(self.app.logger, level='WARNING') as logs:
            result = client.post('/predict', json={'message': 'hello'})
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.get_json()['intent'], 'text_error')
        self.assertIn("isn't available", result.get_json()['reply'])
        self.assertNotIn('Sensitive internal', '\n'.join(logs.output))
        self.assertEqual(client.get('/health').get_json()['chat_model'], 'not_loaded')
        self.assertEqual(client.post('/predict', json={'message': 'I cannot breathe'}).get_json()['intent'], 'emergency')

    def test_requests_waiting_for_startup_receive_a_bounded_retry_response(self):
        busy = Mock()
        busy.acquire.return_value = False
        busy.locked.return_value = True
        with patch('app.Lock', return_value=busy):
            app = create_app(history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        result = client.post('/predict', json={'message': 'hello'})
        self.assertEqual(result.status_code, 503)
        self.assertIn('still starting', result.get_json()['reply'])
        self.assertEqual(client.get('/health').get_json()['chat_model'], 'loading')
        busy.release.assert_not_called()


if __name__ == '__main__':
    unittest.main()
