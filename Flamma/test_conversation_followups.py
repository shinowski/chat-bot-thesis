"""Regression tests for the reported rash/photo conversation and similar wording."""

from copy import deepcopy
import contextlib
import io
import unittest
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from test_image_integration import make_bot


def patient_data(bot):
    """Assert clinical memory independently of reply/question bookkeeping."""
    return {key: deepcopy(value) for key, value in bot.conversation.data.items()
            if key not in {'last_reply_intent', 'pending_question', 'last_knowledge_topics', 'invalid_answers'}}


class FollowupTests(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.bot = make_bot()

    def photo(self):
        return self.bot.reply('', FileStorage(filename='skin.png'))

    def test_reported_conversation_keeps_rash_and_understands_photo_opinions(self):
        self.bot.image_classifier.result['confidence'] = 0.758
        with patch.object(self.bot.classifier, 'predict', side_effect=[
            ('unknown', 0.24), ('greeting', 0.87), ('greeting', 0.85),
            ('image_upload', 0.64), ('unknown', 0.3), ('image_upload', 0.64), ('unknown', 0.24),
        ]):
            self.assertEqual(self.bot.reply('dsds')['intent'], 'unknown')
            self.assertEqual(self.bot.reply('hello')['intent'], 'greeting')
            description = 'i have a skin rashes can you help me'
            rash = self.bot.reply(description)
            self.assertEqual(rash['intent'], 'symptom')
            self.assertIn(description, self.bot.conversation.get('symptoms'))
            self.assertIn('Where', rash['reply'])
            self.assertEqual(self.bot.reply('can i send a photo?')['action'], 'upload_image')
            image = self.photo()
            self.assertNotIn('Can you describe your skin problem', image['reply'])
            unsure = self.bot.reply('i dont know')
            self.assertEqual(unsure['intent'], 'uncertain_answer')
            self.assertEqual(self.bot.conversation.get('location'), 'unknown')
            self.assertNotIn('upload', unsure['reply'].lower())
            before = patient_data(self.bot)
            for message in ['what do you think in that images', 'i mean what is your thoiughts about it']:
                result = self.bot.reply(message)
                self.assertEqual(result['intent'], 'image_explanation')
                self.assertIn('Atopic Dermatitis', result['reply'])
                self.assertIn('75.8%', result['reply'])
                self.assertIn('not a confirmed diagnosis', result['reply'])
                self.assertIsNone(result['action'])
                self.assertEqual(result['confidenceSource'], 'image_model')
                self.assertEqual(result['confidence'], 0.758)
            self.assertEqual(patient_data(self.bot), before)
            self.assertEqual(self.bot.image_classifier.calls, 1)

    def test_help_does_not_hide_symptom_description(self):
        for message in [
            'i have a skin rashes can you help me', 'hello my rash is itchy',
            'can you help me with this rash?', 'could you help with my dry skin',
            'I have red bumps, are you there?', 'my skn has rashesh pls help me',
        ]:
            with self.subTest(message=message):
                bot = make_bot()
                with patch.object(bot.classifier, 'predict', return_value=('greeting', 0.95)):
                    result = bot.reply(message)
                self.assertEqual(result['intent'], 'symptom')
                self.assertIn(message, bot.conversation.get('symptoms'))
                self.assertEqual(bot.flow.get_expected_intent(bot.conversation), 'location')

    def test_photo_opinion_variants_override_upload_and_unknown_guesses(self):
        self.photo()
        before = patient_data(self.bot)
        for message in [
            'what do you think in that images', 'i mean what is your thoiughts about it',
            'what you think of this pic', 'what are your thoughts about that photo?',
            'your opinon on it please', 'what does the photo show?',
            'can you explain the image I uploaded', 'what do you see in this picture',
            'tell me about this result', 'what does it look like', 'your thoughts',
        ]:
            for predicted in ['image_upload', 'unknown', 'greeting']:
                with self.subTest(message=message, predicted=predicted):
                    with patch.object(self.bot.classifier, 'predict', return_value=(predicted, 0.95)):
                        result = self.bot.reply(message)
                    self.assertEqual(result['intent'], 'image_explanation')
                    self.assertIsNone(result['action'])
                    self.assertEqual(patient_data(self.bot), before)
        self.assertEqual(self.bot.image_classifier.calls, 1)

    def test_unknown_symptoms_after_photo_skip_without_inventing_symptoms(self):
        self.photo()
        result = self.bot.reply('idk')
        self.assertEqual(result['intent'], 'uncertain_answer')
        self.assertTrue(self.bot.conversation.get('symptoms_unknown'))
        self.assertEqual(self.bot.conversation.get('symptoms'), [])
        self.assertEqual(self.bot.flow.get_expected_intent(self.bot.conversation), 'location')
        self.assertIn('already have your photo', result['reply'])
        self.assertNotIn('upload', result['reply'].lower())
        self.bot.reply('my arm')
        self.assertEqual(self.bot.flow.get_expected_intent(self.bot.conversation), 'duration')

    def test_no_photo_does_not_fabricate_a_model_result(self):
        with patch.object(self.bot.classifier, 'predict', return_value=('unknown', 0.24)):
            result = self.bot.reply('what do you think in that images')
        self.assertNotEqual(result['intent'], 'image_explanation')
        self.assertFalse(self.bot.conversation.get('image_uploaded'))
        self.assertIsNone(self.bot.conversation.get('classification'))

    def test_explicit_request_still_uploads_when_it_also_mentions_opinion(self):
        self.photo()
        for message in ['can I send another photo and get your thoughts about it?', 'I want to show a picture so you can explain it']:
            with self.subTest(message=message):
                result = self.bot.reply(message)
                self.assertEqual(result['intent'], 'image_request')
                self.assertEqual(result['action'], 'upload_image')

    def test_new_photo_caption_does_not_repeat_the_previous_result(self):
        self.photo()
        self.bot.image_classifier.result.update(predicted_class='psoriasis', condition='Psoriasis')
        result = self.bot.reply('what do you think of this photo?', FileStorage(filename='second.png'))
        self.assertEqual(result['intent'], 'image_classification')
        self.assertIn('Psoriasis', result['reply'])
        self.assertNotIn('Atopic Dermatitis', result['reply'])
        self.assertIn('Psoriasis', self.bot.reply('i mean your thoughts about it')['reply'])

    def test_normal_skin_explanation_has_no_disease_overview(self):
        self.bot.image_classifier.result.update(predicted_class='normal_skin', condition='No Condition Detected')
        self.photo()
        result = self.bot.reply('what do you think about that photo')
        self.assertEqual(result['intent'], 'image_explanation')
        self.assertIn('No Condition Detected', result['reply'])
        self.assertNotIn('Dermatitis', result['reply'])

    def test_medical_questions_and_emergencies_keep_priority(self):
        for message in ['what causes this rash?', 'can you help with psoriasis treatment?']:
            self.assertEqual(self.bot.reply(message)['intent'], 'knowledge_question')
        self.photo()
        for message in ['what do you think about this cream?', 'can you explain this medication?']:
            self.assertEqual(self.bot.reply(message)['intent'], 'knowledge_question')
        with patch.object(self.bot.classifier, 'predict', return_value=('unknown', 0.25)):
            result = self.bot.reply('I cannot breathe, what do you think of that image')
        self.assertEqual(result['intent'], 'emergency')
        self.assertIsNone(result['action'])

    def test_weak_random_text_does_not_fill_any_screening_field(self):
        for intent in ['location', 'symptom', 'duration', 'severity', 'medication']:
            with self.subTest(intent=intent):
                bot = make_bot()
                before = patient_data(bot)
                with patch.object(bot.classifier, 'predict', return_value=(intent, 0.24)):
                    result = bot.reply('dssd')
                self.assertEqual(result['intent'], 'clarification')
                self.assertEqual(patient_data(bot), before)

    def test_unrelated_text_never_becomes_a_screening_fact_regardless_of_confidence(self):
        for message in ['banana', 'lala mo', 'o my god', 'hello world xyz', 'coffee', 'asdf']:
            for intent in ['location', 'duration', 'symptom', 'severity', 'medication']:
                for confidence in [0.36, 0.60, 0.99]:
                    with self.subTest(message=message, intent=intent, confidence=confidence):
                        bot = make_bot()
                        before = patient_data(bot)
                        with patch.object(bot.classifier, 'predict', return_value=(intent, confidence)):
                            result = bot.reply(message)
                        self.assertNotIn(result['intent'], {'location', 'duration', 'symptom', 'severity', 'medication'})
                        self.assertEqual(patient_data(bot), before)

    def test_latest_report_rejects_bad_answers_and_then_accepts_real_details(self):
        with patch.object(self.bot.classifier, 'predict', side_effect=[
            ('greeting', 0.87), ('greeting', 0.80), ('location', 0.60),
            ('duration', 0.36), ('symptom', 0.95), ('symptom', 0.90),
            ('location', 0.90), ('duration', 0.95),
        ]):
            self.bot.reply('hello')
            self.bot.reply('can you help me')
            before = patient_data(self.bot)
            for message in ['banana', 'lala mo', 'o my god']:
                result = self.bot.reply(message)
                self.assertEqual(result['intent'], 'clarification')
                self.assertEqual(patient_data(self.bot), before)
                self.assertNotIn("I've noted", result['reply'])
                self.assertIsNone(result['confidence'])
            self.bot.reply('my skin has a rash')
            self.bot.reply('on my arm')
            result = self.bot.reply('two weeks')
        self.assertIn('medication', result['reply'])
        self.assertEqual(self.bot.conversation.get('location'), 'on my arm')
        self.assertEqual(self.bot.conversation.get('duration'), 'two weeks')

    def test_numbers_are_not_saved_as_symptoms_even_with_confident_guess(self):
        for message in ['123', '456', '123 456']:
            with self.subTest(message=message):
                bot = make_bot()
                with patch.object(bot.classifier, 'predict', return_value=('symptom', 0.99)):
                    result = bot.reply(message)
                self.assertEqual(result['intent'], 'clarification')
                self.assertEqual(bot.conversation.get('symptoms'), [])

    def test_photo_help_caption_does_not_repeat_a_greeting(self):
        with patch.object(self.bot.classifier, 'predict', return_value=('greeting', 0.9)):
            result = self.bot.reply('can you help me', FileStorage(filename='skin.png'))
        self.assertEqual(result['intent'], 'image_classification')
        self.assertTrue(result['reply'].startswith("The image model's closest match"))
        self.assertNotIn('Hello', result['reply'])

    def test_photo_symptom_caption_asks_the_next_question_once(self):
        result = self.bot.reply('my rash is itchy on my arm for two weeks', FileStorage(filename='skin.png'))
        self.assertEqual(result['reply'].count('Have you applied any medication?'), 1)
        self.assertIn('my rash', self.bot.conversation.get('symptoms')[0])

    def test_treatment_answer_after_photo_does_not_restart_the_screening(self):
        self.photo()
        result = self.bot.reply('how can i treat it?')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn(self.bot.knowledge.get('atopic_dermatitis', 'management'), result['reply'])
        self.assertNotIn('To continue the screening', result['reply'])
        self.assertNotIn('Can you describe', result['reply'])
        self.assertIn('Explain simply', result['followUps'])

    def test_medication_numbers_leave_screening_state_unchanged(self):
        self.bot.conversation.add_symptom('rash')
        self.bot.conversation.set('location', 'arm')
        self.bot.conversation.set('duration', 'unknown')
        self.photo()
        before = patient_data(self.bot)
        for message in ['123', '456']:
            result = self.bot.reply(message)
            self.assertEqual(result['intent'], 'invalid_medication')
            self.assertEqual(patient_data(self.bot), before)
        result = self.bot.reply('i dont know')
        self.assertEqual(self.bot.conversation.get('medication'), 'unknown')
        self.assertIsNone(self.bot.flow.get_expected_intent(self.bot.conversation))
        self.assertIn('ask about your photo result', result['reply'])

    def test_greeting_after_a_photo_does_not_repeat_the_startup_question(self):
        self.photo()
        result = self.bot.reply('hello')
        self.assertEqual(result['intent'], 'greeting')
        self.assertIn('photo result', result['reply'])
        self.assertNotIn('describe', result['reply'].lower())


if __name__ == '__main__':
    unittest.main()
