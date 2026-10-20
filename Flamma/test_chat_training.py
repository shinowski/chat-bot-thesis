"""Conversation and training-data regressions independent of classifier luck."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from model.config import PROJECT_DIR, intent_model_path
from model.training_data import example_group, load_training_examples
from test_conversation_followups import patient_data
from test_image_integration import make_bot


class SmarterConversationTests(unittest.TestCase):
    def setUp(self):
        self.bot = make_bot()

    def test_thanks_and_confirmation_keep_the_actual_pending_question(self):
        self.bot.reply('my skin is itchy')
        self.assertIn('Where', self.bot.reply('thanks')['reply'])
        self.assertEqual(self.bot.conversation.get('pending_question'), 'location')
        self.bot.reply('my left wrist')
        self.assertIn('How long', self.bot.reply('yes')['reply'])
        self.assertIsNone(self.bot.conversation.get('duration'))
        self.assertEqual(self.bot.conversation.get('pending_question'), 'duration')

    def test_progressive_medication_reports_do_not_replace_rash_duration_or_location(self):
        self.bot.reply('my rash is itchy on my arm for four weeks')
        old = patient_data(self.bot)
        result = self.bot.reply("I've been applying a cream to my leg for five days")
        self.assertEqual(result['intent'], 'medication')
        self.assertEqual(self.bot.conversation.get('duration'), old['duration'])
        self.assertEqual(self.bot.conversation.get('location'), old['location'])
        self.bot.reply("Actually, I've been using a lotion on my face for three days")
        self.assertEqual(self.bot.conversation.get('duration'), old['duration'])
        self.assertEqual(self.bot.conversation.get('location'), old['location'])
        self.assertIn('lotion', self.bot.conversation.get('medication'))

    def test_negative_medication_answer_is_understood_after_a_question(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        self.assertEqual(self.bot.reply("No, I haven't")['intent'], 'medication')
        self.assertEqual(self.bot.conversation.get('medication'), 'none')

    def test_unrelated_requests_do_not_become_patient_facts(self):
        self.bot.reply('my skin is itchy')
        before = patient_data(self.bot)
        for message in ['Debug my JavaScript', 'Where can I buy a cream-colored sofa?',
                        'My face ID is not working on my phone', 'My car dashboard has a red warning light']:
            self.assertEqual(self.bot.reply(message)['intent'], 'out_of_scope')
            self.assertEqual(patient_data(self.bot), before)

    def test_named_condition_report_is_information_not_a_photo_diagnosis(self):
        result = self.bot.reply('I think I have psoriasis')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn('General information about Psoriasis', result['reply'])
        self.assertIsNone(self.bot.conversation.get('classification'))
        self.assertFalse(self.bot.conversation.get('image_uploaded'))
        self.assertIn(self.bot.knowledge.get('psoriasis', 'management'), self.bot.reply('and treatment?')['reply'])

    def test_capabilities_privacy_and_learning_questions_receive_specific_answers(self):
        with patch.object(self.bot.classifier, 'predict', return_value=('bot_identity', .9)):
            self.assertIn('summarize', self.bot.reply('What can you do?')['reply'])
            self.assertIn('saved on the Flamma server', self.bot.reply('Is my information private?')['reply'])
            self.assertIn('does not automatically train', self.bot.reply('Do you learn from my messages?')['reply'])

    def test_text_only_preference_survives_restore_and_keeps_photo_upload_optional(self):
        self.bot.reply('text only please')
        self.bot.reply('my skin is itchy on my arm for two weeks')
        result = self.bot.reply('none')
        self.assertNotIn('upload', result['reply'].lower())
        self.assertIsNone(self.bot.flow.get_expected_intent(self.bot.conversation))
        restored = make_bot()
        restored.conversation.restore(self.bot.conversation.data)
        self.assertTrue(restored.conversation.get('image_declined'))
        self.assertEqual(restored.reply('Can I upload a photo?')['intent'], 'image_request')
        self.assertFalse(restored.conversation.get('image_declined'))

    def test_anxiety_is_acknowledged_without_inventing_a_condition(self):
        with patch.object(self.bot.classifier, 'predict', return_value=('emergency', .95)):
            result = self.bot.reply("I'm worried about this")
        self.assertEqual(result['intent'], 'emotional_support')
        self.assertIn('one step at a time', result['reply'])
        self.assertIsNone(self.bot.conversation.get('classification'))
        self.assertEqual(self.bot.reply("I'm worried and I cannot breathe")['intent'], 'emergency')


class TrainingDataTests(unittest.TestCase):
    def test_duplicate_normalized_examples_are_removed_and_conflicting_labels_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'examples.json'
            path.write_text(json.dumps({'intents': [
                {'tag': 'greeting', 'patterns': ['Hello', 'hello!', 'hello']},
                {'tag': 'symptom', 'patterns': ['itchy skin', 'mixed label']},
                {'tag': 'location', 'patterns': ['mixed label', 'my arm']},
            ]}), encoding='utf-8')
            examples, audit = load_training_examples([path])
        self.assertEqual(len(examples), 3)
        self.assertEqual(audit['duplicates_removed'], 2)
        self.assertEqual(audit['conflicts_excluded'], ['mixed label'])
        self.assertNotIn('mixed label', [item['text'] for item in examples])

    def test_template_variations_share_a_validation_group(self):
        self.assertEqual(example_group('My left arm is itchy'), example_group('My right leg is dry'))
        self.assertEqual(example_group('for two weeks'), example_group('for seven months'))

    def test_expanded_time_severity_and_product_templates_stay_together(self):
        for left, right in [
            ('The elapsed time is thirteen days', 'The elapsed time is roughly sixteen months'),
            ('The elapsed time is half an hour', 'The elapsed time is a couple of nights'),
            ('For severity, my answer is mild', 'For severity, my answer is bothersome'),
            ('I have already tried a cream', 'I have already tried an ointment'),
        ]:
            self.assertEqual(example_group(left), example_group(right), (left, right))

    def test_broader_english_supplement_is_disjoint_from_evaluation_and_conflicts(self):
        from eval.create_english_intent_supplement import reserve_evaluation_messages
        from model.text_understanding import clean_message
        from model.training_data import default_training_paths
        examples, audit = load_training_examples([
            *default_training_paths(), PROJECT_DIR / 'data/english_location_supplement.json',
            PROJECT_DIR / 'data/english_intent_supplement.json',
        ])
        supplement, _ = load_training_examples([PROJECT_DIR / 'data/english_intent_supplement.json'])
        self.assertFalse({clean_message(item['text']) for item in supplement} & reserve_evaluation_messages())
        self.assertFalse(audit['conflicts_excluded'])
        self.assertEqual(len({row['label'] for row in examples}), 13)

    def test_training_sources_do_not_include_the_frozen_test_messages(self):
        from eval.final_test_cases import FINAL_TEST_CASES
        from model.text_understanding import clean_message
        examples, audit = load_training_examples()
        train = {clean_message(item['text']) for item in examples}
        self.assertFalse(train & {clean_message(text) for text, _ in FINAL_TEST_CASES})
        self.assertEqual(len(audit['sources']), 2)

    def test_manifest_selects_candidate_and_environment_override_preserves_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / 'active.json'
            manifest.write_text(json.dumps({'path': 'artifacts/intent_v3.pkl'}))
            with patch('model.config.ACTIVE_MODEL_MANIFEST', manifest), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(intent_model_path(), PROJECT_DIR / 'artifacts/intent_v3.pkl')
                with patch.dict(os.environ, {'FLAMMA_INTENT_MODEL': 'semantic_classifier.pkl'}):
                    self.assertEqual(intent_model_path(), PROJECT_DIR / 'semantic_classifier.pkl')

    def test_location_supplement_stays_out_of_test_and_keeps_template_families_together(self):
        from eval.final_test_cases import FINAL_TEST_CASES
        from model.text_understanding import clean_message
        from model.training_data import default_training_paths
        examples, audit = load_training_examples([
            *default_training_paths(), PROJECT_DIR / 'data/english_location_supplement.json',
        ])
        self.assertEqual(len(audit['sources']), 3)
        self.assertFalse(audit['conflicts_excluded'])
        self.assertFalse({clean_message(item['text']) for item in examples}
                         & {clean_message(text) for text, _ in FINAL_TEST_CASES})
        self.assertEqual(example_group('The patch I want to discuss sits on my wrist'),
                         example_group('The patch I want to discuss sits on my ankle'))


if __name__ == '__main__':
    unittest.main()
