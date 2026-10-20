"""Personal diagnosis requests must remain distinct from general condition care."""

import unittest
from unittest.mock import patch
from werkzeug.datastructures import FileStorage

from model.knowledge_base import is_diagnosis_question, topic_requests
from test_image_integration import make_bot


class DiagnosisFollowupTests(unittest.TestCase):
    def rejected_photo(self, bot):
        bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
        return bot.reply('', FileStorage(filename='unclear.png'))

    def test_user_sequence_after_rejection_gives_diagnosis_limit_then_treatment(self):
        bot = make_bot()
        self.rejected_photo(bot)
        self.assertNotIn('treatmentInfo', bot.reply('but this is my skin how can I treat this'))
        bot.reply('I think this is rosacea')
        diagnosis = bot.reply('is this my skin conditon?')
        self.assertEqual(diagnosis['intent'], 'diagnosis_question')
        self.assertIn('cannot confirm', diagnosis['reply'])
        self.assertIn('not classified reliably', diagnosis['reply'])
        self.assertIn('Rosacea', diagnosis['reply'])
        treatment = bot.reply('is it treatable?')
        self.assertEqual(treatment['intent'], 'knowledge_question')
        self.assertIn('treatment can help control symptoms', treatment['reply'])
        self.assertLess(len(treatment['reply'].split()), 55)
        self.assertNotIn(bot.knowledge.get('rosacea', 'overview'), treatment['reply'])
        self.assertEqual(treatment['treatmentInfo']['condition_key'], 'rosacea')
        self.assertNotIn('sourceImageId', treatment)
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertFalse(bot.conversation.get('image_uploaded'))

    def test_strong_model_guesses_cannot_turn_personal_diagnosis_questions_into_facts(self):
        for text in ['is this my skin condition?', 'do I really have it?', 'do I have rosacea?',
                     'is this rosacea?', 'could this be rosacea?', 'does this mean I have rosacea?']:
            bot = make_bot()
            bot.reply('I think I have rosacea')
            with patch.object(bot.classifier, 'predict', return_value=('location', .99)):
                result = bot.reply(text)
            self.assertEqual(result['intent'], 'diagnosis_question', text)
            self.assertIsNone(bot.conversation.get('classification'))
            self.assertIsNone(bot.conversation.get('location'))

    def test_treatability_and_curability_use_each_conditions_management_information(self):
        for key, entry in make_bot().knowledge.data.items():
            if key == 'normal_skin':
                continue
            for text in ['is it treatable?', 'is it curable?', 'can it be managed?', 'is it tretable?']:
                bot = make_bot()
                bot.reply('Tell me about ' + entry['name'])
                result = bot.reply(text)
                self.assertEqual(result['intent'], 'knowledge_question', (key, text))
                info = bot.knowledge.treatment_info(key)
                answer_type = 'curability' if 'curable' in text else 'treatability'
                self.assertIn(info['brief_answers'][answer_type], result['reply'])
                self.assertLess(len(result['reply'].split()), 55)
                self.assertEqual(bot.conversation.get('knowledge_disease'), key)

    def test_normal_skin_treatability_does_not_offer_disease_medicine(self):
        bot = make_bot()
        bot.image_classifier.result.update(predicted_class='normal_skin', condition='Normal Skin')
        bot.reply('', FileStorage(filename='skin.png'))
        result = bot.reply('is it treatable?')
        self.assertEqual(result['treatmentInfo']['clinician_options'], [])
        self.assertIsNone(bot.conversation.get('knowledge_disease'))

    def test_diagnosis_question_keeps_the_accepted_photo_as_screening_only(self):
        bot = make_bot()
        bot.reply('', FileStorage(filename='skin.png'))
        result = bot.reply('is this my skin condition?')
        self.assertEqual(result['intent'], 'diagnosis_question')
        self.assertIn('screening suggestion', result['reply'])
        self.assertIn('not a confirmed diagnosis', result['reply'])
        self.assertEqual(bot.conversation.get('classification'), 'dermatitis')
        self.assertEqual(bot.image_classifier.calls, 1)
        self.assertNotIn('treatmentInfo', result)

    def test_explicit_user_named_condition_does_not_replace_a_different_photo_class(self):
        bot = make_bot()
        bot.reply('', FileStorage(filename='skin.png'))
        bot.reply('do I have rosacea?')
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'rosacea')
        self.assertEqual(bot.image_knowledge_disease(), 'atopic_dermatitis')
        treatment = bot.reply('is it treatable?')
        self.assertEqual(treatment['treatmentInfo']['condition_key'], 'rosacea')
        self.assertNotIn('sourceImageId', treatment)
        self.assertEqual(bot.reply('Treatment options for this photo')['treatmentInfo']['condition_key'], 'atopic_dermatitis')

    def test_explicit_photo_question_remains_blocked_after_rejected_photo_and_named_diagnosis_question(self):
        bot = make_bot()
        self.rejected_photo(bot)
        bot.reply('do I have rosacea?')
        treatment = bot.reply('is it treatable?')
        self.assertEqual(treatment['treatmentInfo']['condition_key'], 'rosacea')
        photo = bot.reply('Treatment options for this photo')
        self.assertIn("couldn't reliably classify", photo['reply'])
        self.assertNotIn('treatmentInfo', photo)
        self.assertNotIn('sourceImageId', photo)

    def test_overview_is_brief_and_explicit_treatment_gets_one_care_section(self):
        bot = make_bot()
        overview = bot.reply('I think this is rosacea')
        self.assertIn(bot.knowledge.get('rosacea', 'management'), overview['reply'])
        self.assertNotIn('Treatment options to discuss with a clinician:', overview['reply'])
        treatment = bot.reply('How is it treated?')
        self.assertEqual(treatment['reply'].count('General care:'), 1)
        self.assertIn(bot.knowledge.treatment_text('rosacea'), treatment['reply'])

    def test_treatment_without_a_condition_cannot_invent_one(self):
        bot = make_bot()
        bot.reply('is this my skin condition?')
        result = bot.reply('is it treatable?')
        self.assertNotIn('treatmentInfo', result)
        self.assertIsNone(bot.conversation.get('knowledge_disease'))
        self.assertIsNone(bot.conversation.get('classification'))

    def test_general_condition_questions_do_not_become_personal_diagnosis_questions(self):
        for text in ['Is rosacea contagious?', 'Is rosacea curable?', 'What is rosacea?',
                     'Is it treatable if it is rosacea?', 'What causes rosacea?']:
            self.assertFalse(is_diagnosis_question(text, True), text)
        self.assertEqual(topic_requests('is it curable?'), ['management'])

    def test_diagnosis_and_treatment_in_one_question_answer_both(self):
        bot = make_bot()
        result = bot.reply('do I have rosacea and is it treatable?')
        self.assertEqual(result['intent'], 'diagnosis_question')
        self.assertIn('cannot confirm', result['reply'])
        self.assertIn('treatment can help control symptoms', result['reply'])
        self.assertEqual(result['treatmentInfo']['condition_key'], 'rosacea')

    def test_simple_explanation_of_diagnosis_limit_does_not_repeat_an_overview(self):
        bot = make_bot()
        bot.reply('I think I have rosacea')
        bot.reply('is this my skin condition?')
        result = bot.reply('explain simply')
        self.assertIn('cannot confirm', result['reply'])
        self.assertNotIn(bot.knowledge.get('rosacea', 'overview'), result['reply'])

    def test_diagnosis_and_treatment_questions_cannot_bypass_current_warning_signs(self):
        bot = make_bot()
        self.assertEqual(bot.reply('do I have rosacea? My lips are swollen')['intent'], 'emergency')
        self.assertEqual(bot.reply('is it treatable? I cannot breathe')['intent'], 'emergency')


if __name__ == '__main__':
    unittest.main()
