"""English refinements preserve screening facts and separate questions from use."""

import unittest
from unittest.mock import patch

from model.dialogue import dialogue_act
from model.safety import safety_intent
from test_image_integration import make_bot


class EnglishLanguageImprovementTests(unittest.TestCase):
    def test_natural_timeframes_are_accepted_without_inventing_a_date(self):
        for text in ['since last Tuesday', 'roughly a fortnight', 'my skin is flaky lately']:
            bot = make_bot()
            result = bot.reply(text)
            self.assertEqual(result['intent'], 'duration')
            self.assertEqual(bot.conversation.get('duration'), text)

    def test_forgotten_treatment_is_unknown_rather_than_used_medicine_name(self):
        bot = make_bot()
        bot.reply('my rash is on my arm for four days')
        result = bot.reply("I don't remember which cream I used")
        self.assertEqual(result['intent'], 'uncertain_answer')
        self.assertEqual(bot.conversation.get('medication'), 'unknown')

    def test_specific_treatment_uncertainty_does_not_skip_an_unanswered_location(self):
        bot = make_bot()
        bot.reply('my skin is itchy')
        bot.reply("I don't remember which cream I used")
        self.assertEqual(bot.conversation.get('medication'), 'unknown')
        self.assertIsNone(bot.conversation.get('location'))
        self.assertEqual(bot.conversation.get('pending_question'), 'location')

    def test_named_medication_question_cannot_change_location_or_medication_usage(self):
        bot = make_bot()
        bot.reply('my rash is on my arm for four days')
        location = bot.conversation.get('location')
        with patch.object(bot.classifier, 'predict', return_value=('medication', .99)):
            result = bot.reply('Can I apply hydrocortisone on my face?')
        self.assertEqual(result['intent'], 'product_information')
        self.assertEqual(bot.conversation.get('location'), location)
        self.assertIsNone(bot.conversation.get('medication'))
        self.assertIn('cannot confirm', result['reply'])

    def test_product_pronoun_report_and_correction_preserve_rash_timeframe(self):
        bot = make_bot()
        bot.reply('my rash is on my arm for four weeks')
        old_duration = bot.conversation.get('duration')
        old_location = bot.conversation.get('location')
        bot.reply('Can I use that cream?')
        bot.reply('CeraVe')
        result = bot.reply('actually I used it on my leg for two days')
        self.assertEqual(result['intent'], 'correction')
        self.assertEqual(bot.conversation.get('medication'), 'actually I used it on my leg for two days')
        self.assertEqual(bot.conversation.get('duration'), old_duration)
        self.assertEqual(bot.conversation.get('location'), old_location)

    def test_forgotten_name_and_courtesy_preserve_a_product_question(self):
        bot = make_bot()
        bot.reply('Can I use this cream?')
        self.assertEqual(bot.reply('thanks a lot')['intent'], 'thanks')
        self.assertEqual(bot.reply('I forgot its name')['intent'], 'uncertain_answer')
        self.assertEqual(bot.reply('CeraVe')['intent'], 'product_information')
        self.assertIsNone(bot.conversation.get('medication'))

    def test_synonymous_names_are_one_topic_but_real_alternatives_need_a_choice(self):
        bot = make_bot()
        self.assertEqual(bot.reply('What is atopic dermatitis (eczema)?')['intent'], 'knowledge_question')
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'atopic_dermatitis')
        self.assertEqual(bot.reply('Is it atopic dermatitis or another kind of eczema?')['intent'], 'condition_clarification')

    def test_reported_diagnosis_is_information_and_does_not_establish_photo_classification(self):
        bot = make_bot()
        result = bot.reply('My doctor diagnosed contact dermatitis')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'contact_dermatitis')
        self.assertIsNone(bot.conversation.get('classification'))

    def test_invalid_ordinal_does_not_lose_the_original_topic(self):
        bot = make_bot()
        bot.reply('What causes dermatitis, psoriasis, or rosacea?')
        self.assertEqual(bot.reply('the eighth one')['intent'], 'condition_clarification')
        result = bot.reply('the third one')
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'rosacea')
        self.assertIn(bot.knowledge.get('rosacea', 'causes'), result['reply'])

    def test_negative_pause_request_is_not_treated_as_a_pause(self):
        self.assertEqual(dialogue_act("I don't want to skip screening"), 'screening_resume')
        self.assertEqual(dialogue_act('I just want information, skip the screening'), 'screening_pause')

    def test_hypothetical_medicine_warning_does_not_claim_current_emergency(self):
        self.assertEqual(safety_intent('Can hydrocortisone cause trouble breathing?'), 'safety_information')
        self.assertEqual(make_bot().reply('Can I use hydrocortisone? My throat is swelling')['intent'], 'emergency')


if __name__ == '__main__':
    unittest.main()
