"""Corrections and progress reports must retain the scope of reported facts."""

import json
import unittest

from app import create_app
from model.conversation_language import is_symptom_update
from model.dialogue import correction_updates
from model.text_understanding import duration_mentions
from test_image_integration import make_bot


class CorrectionProgressTests(unittest.TestCase):
    def test_corrections_keep_complete_written_quantities(self):
        for replacement in ['twenty-one days', 'thirteen days', 'a couple of nights',
                            'half an hour', 'a day and a half', '2-3 weeks', 'this morning']:
            for message in [f'Actually, {replacement}, not two weeks', f'Not two weeks, {replacement}']:
                with self.subTest(message=message):
                    bot = make_bot()
                    bot.reply('My rash is on my arm for two weeks')
                    self.assertEqual(bot.reply(message)['intent'], 'correction')
                    self.assertEqual(bot.conversation.get('duration'), replacement)
                    self.assertEqual(bot.conversation.get('location'), 'My rash is on my arm for two weeks')

    def test_rejected_compound_number_is_not_extracted_as_a_smaller_number(self):
        self.assertEqual(correction_updates('Not twenty-three days, thirteen days')['duration'], 'thirteen days')
        self.assertEqual([m.group() for m in duration_mentions('twenty-three days')], ['twenty-three days'])
        self.assertEqual([m.group() for m in duration_mentions('2-3 weeks')], ['2-3 weeks'])

    def test_qualified_body_areas_keep_directions_and_reject_negated_area(self):
        for message, expected in [
            ('Actually, my upper back, not my lower back', 'upper back'),
            ('Not my outer thigh, my inner thigh instead', 'inner thigh'),
            ('Actually, my left inner thigh, not my right inner thigh', 'left inner thigh'),
        ]:
            bot = make_bot()
            bot.reply('My skin is itchy on my arm')
            self.assertEqual(bot.reply(message)['intent'], 'correction')
            self.assertEqual(bot.conversation.get('location'), expected)

    def test_qualified_choices_remain_distinct_and_can_be_selected(self):
        bot = make_bot()
        bot.reply('My skin is itchy')
        self.assertEqual(bot.reply('my upper back or my lower back')['intent'], 'location_clarification')
        self.assertIsNone(bot.conversation.get('location'))
        bot.reply('second one')
        self.assertEqual(bot.conversation.get('location'), 'lower back')
        self.assertIsNone(bot.conversation.get('pending_screening_choices'))

    def test_expanded_time_choices_preserve_whole_phrases(self):
        for message, expected in [('two nights or twenty days', 'twenty days'),
                                  ('2-3 weeks or a day and a half', 'a day and a half')]:
            bot = make_bot()
            bot.reply('My skin is itchy on my arm')
            self.assertEqual(bot.reply(message)['intent'], 'duration_clarification')
            self.assertIsNone(bot.conversation.get('duration'))
            bot.reply('second one')
            self.assertEqual(bot.conversation.get('duration'), expected)

    def test_correction_of_a_choice_does_not_leave_stale_options(self):
        bot = make_bot()
        bot.reply('My skin is itchy on my arm')
        bot.reply('two nights or twenty days')
        bot.reply('Actually, thirteen days')
        self.assertEqual(bot.conversation.get('duration'), 'thirteen days')
        self.assertIsNone(bot.conversation.get('pending_screening_choices'))

    def test_progress_keeps_original_onset_area_and_treatment(self):
        for update in ['The rash has cleared up today', 'The rash has come back today',
                       'The stinging has eased', 'My rash comes and goes',
                       'My skin has been clearing up', 'The rash is flaring up',
                       'My rash is not improving', 'The rash has not cleared up']:
            bot = make_bot()
            report = 'My rash is on my arm for two weeks'
            bot.reply(report)
            bot.reply('I used a cream for three days')
            self.assertEqual(bot.reply(update)['intent'], 'symptom_update', update)
            self.assertEqual(bot.conversation.get('location'), report)
            self.assertEqual(bot.conversation.get('duration'), report)
            self.assertEqual(bot.conversation.get('medication'), 'I used a cream for three days')
            self.assertEqual(bot.conversation.get('symptom_updates'), [update])
            self.assertIsNone(bot.conversation.get('classification'))

    def test_progress_questions_are_not_recorded_as_changes(self):
        for message in ['Has my rash cleared up?', 'My rash has cleared up?',
                        'Will the rash come back?', 'What if the stinging has eased?',
                        'I used a cream because the rash has come back']:
            self.assertFalse(is_symptom_update(message), message)

    def test_progress_does_not_resume_paused_screening_and_warning_signs_win(self):
        bot = make_bot()
        bot.reply('Skip screening')
        bot.reply('The rash has come back today')
        self.assertTrue(bot.conversation.get('screening_paused'))
        self.assertIsNone(bot.conversation.get('pending_question'))
        result = bot.reply('The rash has cleared up but I cannot breathe')
        self.assertEqual(result['intent'], 'emergency')
        self.assertNotIn('treatmentInfo', result)

    def test_saved_corrections_and_changes_survive_restore_with_original_user_text(self):
        app = create_app(make_bot(), history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        for message in ['My rash is on my arm for two weeks',
                        'Actually, twenty-one days, not two weeks', 'The rash has come back today']:
            result = client.post('/predict', json={'message': message}).get_json()
            self.assertEqual(result['messages'][0]['text'], message)
        state = json.loads(app.extensions['chat_history'].db.execute('SELECT state FROM conversations').fetchone()['state'])
        restored = make_bot()
        restored.conversation.restore(state)
        summary = restored.reply('Summarize our conversation')['reply']
        self.assertIn('How long: twenty-one days', summary)
        self.assertIn("Changes you've reported (your words): The rash has come back today", summary)


if __name__ == '__main__':
    unittest.main()
