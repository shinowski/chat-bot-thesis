import unittest
from unittest.mock import patch
from werkzeug.datastructures import FileStorage
from test_image_integration import make_bot


class QuestionClarificationTests(unittest.TestCase):
    def test_two_possible_conditions_require_a_choice_before_treatment(self):
        bot = make_bot()
        result = bot.reply('Could it be eczema or psoriasis? How do I treat it?')
        self.assertEqual(result['intent'], 'condition_clarification')
        self.assertEqual(result['followUps'], ['Dermatitis', 'Psoriasis'])
        self.assertIsNone(bot.conversation.get('knowledge_disease'))
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertNotIn('treatmentInfo', result)
        result = bot.reply('second one')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'psoriasis')
        self.assertIsNone(bot.conversation.get('classification'))

    def test_named_choice_keeps_the_original_question_topic(self):
        bot = make_bot()
        bot.reply('What causes eczema or psoriasis?')
        result = bot.reply('Psoriasis')
        self.assertIn(bot.knowledge.get('psoriasis', 'causes'), result['reply'])
        self.assertEqual(bot.conversation.get('last_knowledge_topics'), ['causes'])

    def test_overlapping_subtype_names_do_not_make_a_false_choice(self):
        bot = make_bot()
        self.assertEqual(bot.knowledge.detect_diseases('What is atopic dermatitis?'), ['atopic_dermatitis'])
        self.assertEqual(bot.reply('What is atopic dermatitis?')['intent'], 'knowledge_question')

    def test_an_explicit_comparison_is_answered_without_picking_a_diagnosis(self):
        bot = make_bot()
        result = bot.reply('What is the difference between eczema and psoriasis?')
        self.assertEqual(result['intent'], 'condition_comparison')
        self.assertIn(bot.knowledge.get('dermatitis', 'overview'), result['reply'])
        self.assertIn(bot.knowledge.get('psoriasis', 'overview'), result['reply'])
        self.assertIsNone(bot.conversation.get('classification'))
        result = bot.reply('and treatment?')
        self.assertEqual(result['intent'], 'condition_clarification')
        self.assertEqual(result['followUps'], ['Dermatitis', 'Psoriasis'])

    def test_unnamed_product_question_and_answer_are_not_medication_reports(self):
        bot = make_bot()
        bot.reply('my skin is itchy on my arm for two weeks')
        old = bot.conversation.get('duration')
        self.assertEqual(bot.reply('Can I use that?')['intent'], 'product_clarification')
        self.assertIsNone(bot.conversation.get('medication'))
        result = bot.reply('hydrocortisone')
        self.assertEqual(result['intent'], 'product_information')
        self.assertIsNone(bot.conversation.get('medication'))
        self.assertEqual(bot.conversation.get('duration'), old)

    def test_product_question_uses_named_topic_for_general_information(self):
        bot = make_bot()
        bot.reply('Can I use this cream for psoriasis?')
        result = bot.reply('hydrocortisone')
        self.assertEqual(result['intent'], 'product_information')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'psoriasis')
        self.assertIn('clinician or pharmacist', result['reply'])
        self.assertIsNone(bot.conversation.get('medication'))

    def test_actual_medication_usage_is_still_recorded_after_clarification(self):
        bot = make_bot()
        bot.reply('Can I use that?')
        result = bot.reply('I used hydrocortisone')
        self.assertEqual(result['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), 'I used hydrocortisone')

    def test_conflicting_durations_do_not_overwrite_duration(self):
        bot = make_bot()
        bot.reply('my rash is itchy on my arm for two weeks')
        old = bot.conversation.get('duration')
        result = bot.reply('maybe two days or two months')
        self.assertEqual(result['intent'], 'duration_clarification')
        self.assertEqual(bot.conversation.get('duration'), old)
        self.assertEqual(bot.conversation.get('pending_question'), 'duration')
        bot.reply('three days')
        self.assertEqual(bot.conversation.get('duration'), 'three days')

    def test_possible_body_areas_are_clarified_but_both_is_a_valid_answer(self):
        bot = make_bot()
        bot.reply('my skin is itchy')
        result = bot.reply('maybe my arm or my leg')
        self.assertEqual(result['intent'], 'location_clarification')
        self.assertIsNone(bot.conversation.get('location'))
        self.assertEqual(bot.reply('both my arm and leg')['intent'], 'location')

    def test_vague_question_does_not_change_photo_result(self):
        bot = make_bot()
        bot.reply('', FileStorage(filename='skin.png'))
        old = bot.conversation.get('classification')
        result = bot.reply('is this okay?')
        self.assertEqual(result['intent'], 'question_clarification')
        self.assertEqual(bot.conversation.get('classification'), old)
        self.assertNotIn('treatmentInfo', result)

    def test_explicit_warning_keeps_priority_over_ambiguous_questions(self):
        self.assertEqual(make_bot().reply('Can I use that? I cannot breathe')['intent'], 'emergency')
        self.assertEqual(make_bot().reply('Could it be eczema or psoriasis? My lips are swollen')['intent'], 'emergency')

    def test_ambiguous_condition_names_do_not_replace_a_photo_match(self):
        bot = make_bot()
        bot.reply('', FileStorage(filename='skin.png'))
        bot.reply('Is it psoriasis or rosacea?')
        self.assertEqual(bot.image_knowledge_disease(), 'atopic_dermatitis')
        bot.reply('Psoriasis')
        self.assertEqual(bot.image_knowledge_disease(), 'atopic_dermatitis')
        self.assertEqual(bot.reply('Treatment options for this photo')['treatmentInfo']['condition_key'], 'atopic_dermatitis')

    def test_doctor_question_with_two_possible_conditions_stays_general(self):
        bot = make_bot()
        result = bot.reply('Should I see a doctor for eczema or psoriasis?')
        self.assertIn('Seek medical care promptly if', result['reply'])
        self.assertIsNone(bot.conversation.get('knowledge_disease'))
        self.assertEqual(bot.reply('and treatment?')['intent'], 'condition_clarification')


if __name__ == '__main__':
    unittest.main()
