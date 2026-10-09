"""Disease explanations follow names and accepted photo context, never guesses."""

import contextlib
import io
import unittest
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from test_conversation_followups import patient_data
from test_image_integration import make_bot


class DiseaseExplanationTests(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.bot = make_bot()

    def photo(self, raw, name):
        self.bot.image_classifier.result.update(predicted_class=raw, condition=name)
        return self.bot.reply('', FileStorage(filename='skin.png'))

    def test_every_named_condition_has_an_explanation_with_common_signs_and_care(self):
        for key, entry in self.bot.knowledge.data.items():
            if key == 'normal_skin':
                continue
            with self.subTest(condition=key):
                bot = make_bot()
                result = bot.reply(f"what is {entry['name']}?")
                self.assertEqual(result['intent'], 'knowledge_question')
                for topic in ['overview', 'symptoms', 'management']:
                    self.assertIn(entry[topic], result['reply'])
                self.assertEqual(bot.conversation.get('knowledge_disease'), key)
                self.assertEqual(bot.conversation.get('symptoms'), [])
                self.assertFalse(bot.conversation.get('image_uploaded'))

    def test_generic_disease_question_explains_each_accepted_model_class(self):
        for raw, name in [('atopic_dermatitis', 'Atopic Dermatitis'), ('contact_dermatitis', 'Contact Dermatitis'),
                          ('lichen_planus', 'Lichen Planus'), ('psoriasis', 'Psoriasis'), ('rosacea', 'Rosacea')]:
            with self.subTest(raw=raw):
                self.bot = make_bot()
                self.photo(raw, name)
                before = patient_data(self.bot)
                result = self.bot.reply('what is this disease')
                self.assertEqual(result['intent'], 'knowledge_question')
                self.assertIn(self.bot.knowledge.get(raw, 'overview'), result['reply'])
                self.assertIn('not a confirmed diagnosis', result['reply'])
                self.assertEqual(patient_data(self.bot), before)
                self.assertIsNone(result['action'])
                self.assertEqual(self.bot.image_classifier.calls, 1)

    def test_normal_skin_is_explained_as_a_screening_label(self):
        self.photo('normal_skin', 'No Condition Detected')
        result = self.bot.reply('what is this disease?')
        self.assertIn('not a disease', result['reply'])
        self.assertIn('does not confirm', result['reply'])
        self.assertIsNone(self.bot.conversation.get('knowledge_disease'))
        self.assertNotIn('General care:', result['reply'])

    def test_no_context_offers_condition_choices_without_diagnosing(self):
        result = self.bot.reply('what is this disease?')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn("don't have a disease name", result['reply'])
        self.assertEqual(result['followUps'], self.bot.knowledge.choices())
        self.assertIsNone(self.bot.conversation.get('classification'))
        self.assertIsNone(self.bot.conversation.get('knowledge_disease'))

    def test_symptoms_alone_do_not_establish_a_disease(self):
        self.bot.reply('my rash is itchy on my arm')
        result = self.bot.reply('what disease is this?')
        self.assertIn("don't have a disease name", result['reply'])
        self.assertIsNone(self.bot.conversation.get('classification'))
        self.assertEqual(self.bot.conversation.get('symptoms'), ['my rash is itchy on my arm'])

    def test_named_disease_choices_start_a_topic_for_generic_questions(self):
        self.bot.reply('what is this disease')
        for name in self.bot.knowledge.choices():
            with self.subTest(name=name):
                self.assertEqual(self.bot.reply(name)['intent'], 'knowledge_question')
                result = self.bot.reply('tell me about this condition')
                self.assertIn(f'General information about {name}', result['reply'])

    def test_disease_question_paraphrases_and_typos_interrupt_screening(self):
        for phrase in ['what is this disease', 'what is that condition?', 'explain this disease please',
                       'what disease is this?', 'what is this skin condition', 'what is this desease?',
                       'can you explain the disease?', 'tell me about this disease']:
            with self.subTest(phrase=phrase):
                self.bot = make_bot()
                self.photo('psoriasis', 'Psoriasis')
                with patch.object(self.bot.classifier, 'predict', return_value=('location', 0.99)):
                    result = self.bot.reply(phrase)
                self.assertEqual(result['intent'], 'knowledge_question')
                self.assertIn(self.bot.knowledge.get('psoriasis', 'overview'), result['reply'])
                self.assertIsNone(self.bot.conversation.get('location'))

    def test_specific_subtype_is_matched_before_generic_dermatitis(self):
        for message, key in [('what is atopic dermatitis', 'atopic_dermatitis'),
                             ('what is contact dermatitis', 'contact_dermatitis'),
                             ('allergic contact dermatitis', 'contact_dermatitis'),
                             ('atopic eczema', 'atopic_dermatitis'),
                             ('what is urticara', 'hives'), ('what is dermatitis', 'dermatitis')]:
            with self.subTest(message=message):
                self.assertEqual(self.bot.knowledge.detect_disease(message), key)
                result = self.bot.reply(message)
                self.assertIn(self.bot.knowledge.get(key, 'overview'), result['reply'])

    def test_explicit_name_overrides_the_last_photo_disease(self):
        self.photo('atopic_dermatitis', 'Atopic Dermatitis')
        result = self.bot.reply('tell me about contact dermatitis')
        self.assertIn(self.bot.knowledge.get('contact_dermatitis', 'overview'), result['reply'])
        self.assertNotIn(self.bot.knowledge.get('atopic_dermatitis', 'overview'), result['reply'])
        self.assertIn('Contact Dermatitis', self.bot.reply('what is this disease')['reply'])
        result = self.bot.reply('what is this disease in my photo?')
        self.assertIn(self.bot.knowledge.get('atopic_dermatitis', 'overview'), result['reply'])

    def test_rejected_photo_does_not_receive_a_disease_explanation_from_an_old_photo(self):
        self.photo('psoriasis', 'Psoriasis')
        self.bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
        self.bot.reply('', FileStorage(filename='new.png'))
        result = self.bot.reply('what is this disease?')
        self.assertIn("couldn't reliably classify", result['reply'])
        self.assertNotIn(self.bot.knowledge.get('psoriasis', 'overview'), result['reply'])

    def test_named_condition_can_still_be_discussed_after_a_photo_rejection(self):
        self.bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
        self.bot.reply('', FileStorage(filename='new.png'))
        self.bot.reply('what is contact dermatitis?')
        result = self.bot.reply('and treatment?')
        self.assertIn(self.bot.knowledge.get('contact_dermatitis', 'management'), result['reply'])

    def test_disease_questions_do_not_change_emergency_priority(self):
        result = self.bot.reply('I cannot breathe, what is this disease?')
        self.assertEqual(result['intent'], 'emergency')
        self.assertIsNone(self.bot.conversation.get('knowledge_disease'))


if __name__ == '__main__':
    unittest.main()
