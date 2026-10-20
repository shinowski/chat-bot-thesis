"""Patient facts must retain the meaning of reports and short follow-ups."""

import unittest
from unittest.mock import patch

from app import create_app
from model.dialogue import medication_report_parts
from model.text_understanding import symptom_mentions
from test_image_integration import make_bot


class FollowupContextTests(unittest.TestCase):
    def test_combined_report_separates_rash_time_and_treatment_time_in_both_orders(self):
        for message, location, medication in [
            ('My rash is on my arm for two weeks and I used a cream for three days',
             'My rash is on my arm for two weeks', 'I used a cream for three days'),
            ('I used a cream for three days; my rash is on my leg for two weeks',
             'my rash is on my leg for two weeks', 'I used a cream for three days'),
        ]:
            with self.subTest(message=message):
                bot = make_bot()
                result = bot.reply(message)
                self.assertEqual(result['intent'], 'medication')
                self.assertEqual(bot.conversation.get('location'), location)
                self.assertEqual(bot.conversation.get('duration'), location)
                self.assertEqual(bot.conversation.get('medication'), medication)
                self.assertEqual(bot.conversation.get('pending_question'), 'image_upload')
                self.assertIsNone(bot.conversation.get('classification'))
                self.assertIn('Rash area and timeframe (your words): ' + location, result['reply'])
                self.assertIn('Treatment use (your words): ' + medication, result['reply'])
                self.assertEqual(result['action'], 'upload_image')
                self.assertIn('Text only', result['followUps'])

    def test_photo_step_offers_text_only_without_losing_reported_details(self):
        bot = make_bot()
        bot.reply('My rash is on my arm for two weeks and I used a cream for three days')
        result = bot.reply('Text only')
        self.assertEqual(result['intent'], 'image_declined')
        self.assertIsNone(result['action'])
        self.assertIsNone(bot.conversation.get('pending_question'))
        self.assertEqual(bot.conversation.get('duration'), 'My rash is on my arm for two weeks')
        self.assertEqual(bot.conversation.get('medication'), 'I used a cream for three days')

    def test_standalone_treatment_cannot_overwrite_rash_area_duration_or_severity(self):
        bot = make_bot()
        description = 'My rash is mild on my arm for two weeks'
        bot.reply(description)
        bot.reply('I used cream on my leg for severe acne last year')
        for key in ['location', 'duration', 'severity']:
            self.assertEqual(bot.conversation.get(key), description, key)

    def test_combined_new_concern_clears_old_facts_and_separates_new_treatment(self):
        bot = make_bot()
        bot.reply('My rash is on my leg for four months')
        result = bot.reply('I have a new rash on my arm for two weeks and I used a cream for three days')
        self.assertEqual(result['intent'], 'new_concern')
        self.assertEqual(bot.conversation.get('duration'), 'I have a new rash on my arm for two weeks')
        self.assertEqual(bot.conversation.get('medication'), 'I used a cream for three days')

    def test_new_photo_clears_transient_short_answer_references(self):
        from werkzeug.datastructures import FileStorage
        for message in ['My arm or leg', 'I used it yesterday']:
            bot = make_bot()
            bot.reply(message)
            bot.reply('', FileStorage(filename='skin.png'))
            self.assertIsNone(bot.conversation.get('pending_screening_choices'))
            self.assertIsNone(bot.conversation.get('pending_medication_report'))

    def test_unclear_clause_does_not_manufacture_symptom_duration_or_area(self):
        for text in ['I used a cream on my leg for three days',
                     'I used a cream for three days and my arm was the application site']:
            bot = make_bot()
            bot.reply(text)
            self.assertIsNone(bot.conversation.get('location'))
            self.assertIsNone(bot.conversation.get('duration'))

    def test_question_clause_is_not_a_rash_self_report(self):
        skin, medication = medication_report_parts('I used a cream; can my rash last two weeks?')
        self.assertEqual(skin, [])
        self.assertEqual(medication, 'I used a cream')
        bot = make_bot()
        bot.update_conversation('medication', 'I used a cream; can my rash last two weeks?')
        self.assertEqual(bot.conversation.get('symptoms'), [])
        self.assertIsNone(bot.conversation.get('duration'))

    def test_both_location_choices_survive_restore(self):
        bot = make_bot()
        bot.reply('My skin is itchy')
        result = bot.reply('maybe my arm or my leg')
        self.assertEqual(result['followUps'], ['arm', 'leg', 'Both areas', "I'm not sure"])
        restored = make_bot()
        restored.conversation.restore(bot.conversation.data)
        result = restored.reply('both of them')
        self.assertEqual(result['intent'], 'location')
        self.assertEqual(restored.conversation.get('location'), 'arm and leg')
        self.assertEqual(restored.conversation.get('pending_question'), 'duration')
        self.assertIsNone(restored.conversation.get('pending_screening_choices'))

    def test_duration_choice_keeps_units_and_survives_courtesy(self):
        bot = make_bot()
        bot.reply('My rash is on my arm')
        bot.reply('two days or two weeks')
        bot.reply('thanks')
        self.assertEqual(bot.reply('the second one')['intent'], 'duration')
        self.assertEqual(bot.conversation.get('duration'), 'two weeks')

    def test_out_of_range_choice_retains_pending_options(self):
        bot = make_bot()
        bot.reply('two days or two weeks')
        self.assertEqual(bot.reply('the third one')['intent'], 'duration_clarification')
        self.assertIsNone(bot.conversation.get('duration'))
        bot.reply('first')
        self.assertEqual(bot.conversation.get('duration'), 'two days')

    def test_choices_are_cleared_when_topic_changes_or_user_is_unsure(self):
        for text in ['What is psoriasis?', "I'm not sure", 'new skin concern']:
            bot = make_bot()
            bot.reply('my arm or my leg')
            bot.reply(text)
            self.assertIsNone(bot.conversation.get('pending_screening_choices'))

    def test_explicit_negated_replacements_keep_only_affirmative_facts(self):
        for text, field, value in [('Not two days, two weeks', 'duration', 'two weeks'),
                                   ('Not my arm, my leg', 'location', 'leg')]:
            bot = make_bot()
            bot.reply('My rash is on my arm for three days')
            self.assertEqual(bot.reply(text)['intent'], 'correction')
            self.assertEqual(bot.conversation.get(field), value)

    def test_known_product_reference_is_information_with_no_usage_inference(self):
        bot = make_bot()
        bot.reply('Can I use this cream?')
        bot.reply('CeraVe')
        result = bot.reply('Can I apply it on my face?')
        self.assertEqual(result['intent'], 'product_information')
        self.assertIn('CeraVe', result['reply'])
        self.assertIsNone(bot.conversation.get('medication'))
        self.assertIsNone(bot.conversation.get('location'))
        self.assertEqual(bot.reply('Can I use a different cream?')['intent'], 'product_clarification')

    def test_unknown_product_usage_does_not_replace_rash_timeframe(self):
        bot = make_bot()
        description = 'My rash is on my arm for two weeks'
        bot.reply(description)
        result = bot.reply('I used it yesterday')
        self.assertEqual(result['intent'], 'medication_clarification')
        self.assertEqual(bot.conversation.get('duration'), description)
        bot.reply('thanks')
        self.assertEqual(bot.reply('a moisturizer')['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), 'I used it yesterday; product: a moisturizer')
        self.assertEqual(bot.conversation.get('duration'), description)
        self.assertIsNone(bot.conversation.get('pending_medication_report'))

    def test_negative_usage_records_none_without_requiring_a_product_name(self):
        for text in ["I haven't used anything yet", "I haven't applied anything for this rash"]:
            bot = make_bot()
            with patch.object(bot.classifier, 'predict', return_value=('emergency', .99)):
                result = bot.reply(text)
            self.assertEqual(result['intent'], 'medication')
            self.assertEqual(bot.conversation.get('medication'), 'none')

    def test_named_product_can_be_explicitly_not_used(self):
        bot = make_bot()
        bot.reply('Can I use this cream?')
        bot.reply('CeraVe')
        self.assertEqual(bot.reply("I haven't used it")['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), 'none')

    def test_negative_usage_does_not_negate_a_rash_description(self):
        self.assertEqual(symptom_mentions("I haven't applied anything for this rash"), ({'rash'}, set()))
        self.assertEqual(symptom_mentions('No cream for my itchy rash'), ({'itchy', 'rash'}, set()))
        self.assertEqual(symptom_mentions('I have not used cream and I have no itching'), (set(), {'itching'}))

    def test_unknown_product_not_used_does_not_require_a_name(self):
        bot = make_bot()
        self.assertEqual(bot.reply("I haven't used it")['intent'], 'medication')
        self.assertEqual(bot.conversation.get('medication'), 'none')

    def test_actual_usage_of_remembered_brand_preserves_rash_details(self):
        for usage, expected in [('I used CeraVe on my leg for three days', 'I used CeraVe on my leg for three days'),
                                ("I haven't used CeraVe", 'none')]:
            bot = make_bot()
            description = 'My rash is on my arm for two weeks'
            bot.reply(description)
            bot.reply('Can I use that cream?')
            bot.reply('CeraVe')
            self.assertEqual(bot.reply(usage)['intent'], 'medication')
            self.assertEqual(bot.conversation.get('medication'), expected)
            self.assertEqual(bot.conversation.get('location'), description)
            self.assertEqual(bot.conversation.get('duration'), description)

    def test_warning_signs_take_priority_over_every_pending_choice(self):
        for initial in ['My arm or leg', 'two days or two weeks', 'I used it yesterday']:
            bot = make_bot()
            bot.reply(initial)
            self.assertEqual(bot.reply('both and I cannot breathe')['intent'], 'emergency')

    def test_saved_user_message_preserves_original_combined_wording(self):
        app = create_app(make_bot(), history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        message = 'My rash is on my arm for two weeks and I used a cream for three days'
        response = client.post('/predict', json={'message': message}).get_json()
        self.assertEqual(response['messages'][0]['text'], message)
        row = app.extensions['chat_history'].db.execute('SELECT state FROM conversations').fetchone()
        import json
        self.assertEqual(json.loads(row['state'])['duration'], 'My rash is on my arm for two weeks')


if __name__ == '__main__':
    unittest.main()
