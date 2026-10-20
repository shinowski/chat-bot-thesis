"""Misspellings and subject-only follow-ups must not retain the wrong condition."""

import unittest
from unittest.mock import patch
from werkzeug.datastructures import FileStorage

from model.text_understanding import normalize_message
from test_image_integration import make_bot


class TopicSwitchTests(unittest.TestCase):
    def test_user_roscea_sequence_switches_from_dermatitis_without_creating_a_diagnosis(self):
        bot = make_bot()
        bot.reply('I think this is dermatitis')
        bot.reply('Is it treatable')
        result = bot.reply('how about roscea')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn('Rosacea treatment', result['reply'])
        self.assertNotIn('Dermatitis has treatment options', result['reply'])
        self.assertLess(len(result['reply'].split()), 55)
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'rosacea')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'rosacea')
        bot.reply('I have roscea')
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertEqual(bot.conversation.get('symptoms'), [])
        result = bot.reply('in my butt')
        self.assertIn('Rosacea mainly affects the face', result['reply'])
        result = bot.reply('is it treatable?')
        self.assertIn('Rosacea treatment', result['reply'])
        self.assertIn('I cannot assume rosacea is its cause', result['reply'])
        self.assertNotIn('About Dermatitis', result['reply'])

    def test_question_mark_or_politeness_does_not_change_subject_switch(self):
        for text in ['how about roscea', 'how about roscea?', 'what about roscea', 'what about roscea please']:
            bot = make_bot()
            bot.reply('Is dermatitis treatable?')
            with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
                result = bot.reply(text)
            self.assertEqual(result['intent'], 'knowledge_question', text)
            self.assertIn('Rosacea treatment', result['reply'])

    def test_each_supported_condition_can_replace_a_causes_topic(self):
        for key, entry in make_bot().knowledge.data.items():
            if key == 'normal_skin':
                continue
            bot = make_bot()
            bot.reply('What causes psoriasis?')
            result = bot.reply('how about ' + entry['name'])
            self.assertEqual(bot.conversation.get('knowledge_disease'), key)
            self.assertIn(entry['causes'], result['reply'])
            self.assertIsNone(bot.conversation.get('classification'))

    def test_curability_switch_keeps_the_topic_and_short_answer_style_after_restore(self):
        bot = make_bot()
        bot.reply('Is dermatitis curable?')
        restored = make_bot()
        restored.conversation.restore(bot.conversation.data)
        result = restored.reply('what about roscea')
        self.assertIn('Rosacea has no current cure', result['reply'])
        self.assertLess(len(result['reply'].split()), 55)
        self.assertEqual(restored.conversation.get('last_management_style'), 'curability')

    def test_subject_switch_without_history_is_general_information(self):
        bot = make_bot()
        result = bot.reply('how about roscea')
        self.assertIn(bot.knowledge.get('rosacea', 'overview'), result['reply'])
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertEqual(bot.conversation.get('symptoms'), [])

    def test_explicit_topic_beats_inherited_topic(self):
        bot = make_bot()
        bot.reply('Is dermatitis curable?')
        result = bot.reply('What causes roscea?')
        self.assertIn(bot.knowledge.get('rosacea', 'causes'), result['reply'])
        self.assertIsNone(bot.conversation.get('last_management_style'))

    def test_new_photo_and_new_concern_clear_inherited_style(self):
        for message in ['new skin concern', None]:
            bot = make_bot()
            bot.reply('Is dermatitis treatable?')
            if message is None:
                bot.reply('', FileStorage(filename='skin.png'))
            else:
                bot.reply(message)
            self.assertIsNone(bot.conversation.get('last_management_style'))

    def test_information_topic_never_replaces_an_accepted_photo_label(self):
        bot = make_bot()
        bot.reply('', FileStorage(filename='skin.png'))
        bot.reply('Is it treatable?')
        switched = bot.reply('how about roscea')
        self.assertEqual(switched['treatmentInfo']['condition_key'], 'rosacea')
        self.assertNotIn('sourceImageId', switched)
        self.assertEqual(bot.image_knowledge_disease(), 'atopic_dermatitis')
        self.assertEqual(bot.reply('Treatment options for this photo')['treatmentInfo']['condition_key'], 'atopic_dermatitis')

    def test_nonfacial_concern_asks_for_assessment_instead_of_applying_facial_care(self):
        bot = make_bot()
        bot.reply('I have roscea')
        bot.reply('in my butt')
        result = bot.reply('What can I do next?')
        self.assertIn('Arrange an assessment of the skin concern', result['reply'])
        self.assertNotIn('SPF 30', result['reply'])
        self.assertIsNone(bot.conversation.get('classification'))
        bot.reply('actually on my face, not my butt')
        result = bot.reply('is it treatable?')
        self.assertNotIn('buttocks', result['reply'])

    def test_known_spelling_corrections_preserve_medication_names_and_numbers(self):
        self.assertEqual(normalize_message('roscea rosecea rosace'), 'rosacea rosacea rosacea')
        self.assertEqual(normalize_message('Nivolumab 5 mg rosceazole'), 'nivolumab 5 mg rosceazole')

    def test_actual_warning_signs_beat_the_subject_switch(self):
        bot = make_bot()
        self.assertEqual(bot.reply('how about roscea, I cannot breathe')['intent'], 'emergency')


if __name__ == '__main__':
    unittest.main()
