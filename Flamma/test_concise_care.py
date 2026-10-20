"""Treatment outcome questions and actionable next steps need different replies."""

import unittest
from unittest.mock import patch

from model.knowledge_base import management_style
from test_image_integration import make_bot


class ConciseCareTests(unittest.TestCase):
    def test_user_dermatitis_sequence_answers_shortly_then_asks_missing_location(self):
        bot = make_bot()
        bot.reply('hello')
        report = 'I have a rashes I think this is dermatitis'
        bot.reply(report)
        for text in ['is it treatable?', 'is it treatable']:
            result = bot.reply(text)
            self.assertIn('Dermatitis has treatment options', result['reply'])
            self.assertLess(len(result['reply'].split()), 55)
            self.assertNotIn('Treatment options to discuss with a clinician:', result['reply'])
        next_step = bot.reply('What can I do next?')
        self.assertIn('1.', next_step['reply'])
        self.assertIn('Where is the affected area located?', next_step['reply'])
        self.assertEqual(next_step['followUps'], ['My arm', 'My face', "I'm not sure"])
        self.assertEqual(bot.conversation.get('symptoms'), [report])
        self.assertIsNone(bot.conversation.get('classification'))
        bot.reply('my arm')
        self.assertEqual(bot.conversation.get('pending_question'), 'duration')

    def test_known_area_and_rash_timeframe_are_not_asked_again(self):
        bot = make_bot()
        report = 'My rash is on my arm for two weeks, I think this is dermatitis'
        bot.reply(report)
        result = bot.reply('What can I do next?')
        self.assertIn('Have you applied any medication?', result['reply'])
        self.assertNotIn('Where is the affected area', result['reply'])
        self.assertEqual(bot.reply('none')['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), 'none')
        self.assertEqual(bot.conversation.get('duration'), report)

    def test_long_treatment_is_available_when_explicitly_requested_after_a_short_answer(self):
        bot = make_bot()
        bot.reply('I think this is rosacea')
        brief = bot.reply('is it treatable?')
        self.assertIn('Treatment options for Rosacea', brief['followUps'])
        full = bot.reply('Treatment options for Rosacea')
        self.assertIn(bot.knowledge.treatment_text('rosacea'), full['reply'])
        self.assertNotEqual(brief['reply'], full['reply'])

    def test_cure_and_treatability_are_separate_and_not_a_personal_diagnosis(self):
        bot = make_bot()
        bot.reply('I think this is rosacea')
        treatment = bot.reply('is it treatable?')
        cure = bot.reply('is it curable?')
        self.assertNotEqual(treatment['reply'], cure['reply'])
        self.assertIn('no current cure', cure['reply'])
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertIsNone(bot.conversation.get('medication'))

    def test_question_without_a_condition_never_gets_a_yes_or_a_treatment_profile(self):
        bot = make_bot()
        with patch.object(bot.classifier, 'predict', return_value=('medication', .99)):
            result = bot.reply('is it treatable?')
        self.assertNotIn('treatmentInfo', result)
        self.assertIsNone(bot.conversation.get('knowledge_disease'))

    def test_paused_screening_is_not_resumed_by_a_next_step_question(self):
        bot = make_bot()
        bot.reply('I think this is dermatitis')
        bot.reply('Skip the questions')
        result = bot.reply('What can I do next?')
        self.assertIn('1.', result['reply'])
        self.assertNotIn('Can you describe your skin problem?', result['reply'])
        self.assertIsNone(bot.conversation.get('pending_question'))
        self.assertTrue(bot.conversation.get('screening_paused'))

    def test_prompted_next_step_survives_conversation_restore(self):
        bot = make_bot()
        bot.reply('My rash is on my arm for two weeks, I think this is dermatitis')
        bot.reply('What can I do next?')
        restored = make_bot()
        restored.conversation.restore(bot.conversation.data)
        self.assertEqual(restored.reply('none')['intent'], 'medication')
        self.assertEqual(restored.conversation.get('medication'), 'none')

    def test_unrelated_information_request_does_not_keep_a_previous_screening_prompt(self):
        bot = make_bot()
        bot.reply('I have a rash I think this is dermatitis')
        bot.reply('What can I do next?')
        result = bot.reply('What causes rosacea?')
        self.assertNotIn('Where is the affected area located?', result['reply'])
        self.assertIsNone(bot.conversation.get('pending_question'))

    def test_current_warning_signs_take_priority_over_short_answers_and_next_steps(self):
        bot = make_bot()
        bot.reply('I think this is dermatitis')
        for text in ['is it treatable? I cannot breathe', 'What can I do next? My throat is swollen']:
            self.assertEqual(bot.reply(text)['intent'], 'emergency')

    def test_brief_answers_keep_condition_sources_and_their_review_date(self):
        bot = make_bot()
        bot.reply('I think this is psoriasis')
        result = bot.reply('is it curable?')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'psoriasis')
        self.assertEqual(result['treatmentInfo']['source_checked_on'], '2026-10-15')
        self.assertTrue(result['treatmentInfo']['sources'])
        self.assertNotIn('sourceImageId', result)

    def test_multi_topic_questions_keep_each_requested_topic(self):
        bot = make_bot()
        result = bot.reply('What causes rosacea and how is it treated?')
        self.assertIn(bot.knowledge.get('rosacea', 'causes'), result['reply'])
        self.assertIn(bot.knowledge.get('rosacea', 'management'), result['reply'])

    def test_asking_how_to_treat_is_not_the_same_as_asking_whether_it_is_treatable(self):
        self.assertIsNone(management_style('How is dermatitis treated?'))
        self.assertEqual(management_style('is it treatable'), 'treatability')
        self.assertEqual(management_style('Is it curable?'), 'curability')
        self.assertEqual(management_style('What can I do next?'), 'next_steps')


if __name__ == '__main__':
    unittest.main()
