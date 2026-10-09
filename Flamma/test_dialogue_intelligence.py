"""Conversation regressions independent of the trained model's guesses."""

import contextlib
import io
import unittest

from werkzeug.datastructures import FileStorage

from test_conversation_followups import patient_data
from test_image_integration import make_bot


class DialogueTests(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.bot = make_bot()

    def photo(self):
        return self.bot.reply('', FileStorage(filename='skin.png'))

    def test_uncertainty_after_care_keeps_patient_fields_unchanged(self):
        self.photo()
        self.bot.reply('how can i treat it?')
        before = patient_data(self.bot)
        result = self.bot.reply('idk')
        self.assertIn('shorter explanation', result['reply'])
        self.assertEqual(patient_data(self.bot), before)
        self.assertIsNone(self.bot.conversation.get('pending_question'))

    def test_simple_explanation_keeps_the_topic_after_uncertainty(self):
        self.bot.reply('what causes psoriasis?')
        self.bot.reply('i dont know')
        result = self.bot.reply('explane simply')
        self.assertEqual(result['intent'], 'simple_explanation')
        self.assertIn('Short version', result['reply'])
        self.assertIn(self.bot.knowledge.get('psoriasis', 'causes').split('.')[0], result['reply'])
        self.assertEqual(self.bot.conversation.get('symptoms'), [])

    def test_short_topic_followups_use_the_last_condition(self):
        self.bot.reply('whats eczema')
        for message, topic in [('and causes?', 'causes'), ('what next?', 'management'), ('and treatment', 'management'), ('and contagious?', 'contagious')]:
            with self.subTest(message=message):
                result = self.bot.reply(message)
                self.assertEqual(result['intent'], 'knowledge_question')
                self.assertIn(self.bot.knowledge.get('dermatitis', topic), result['reply'])
                self.assertEqual(self.bot.conversation.get('knowledge_disease'), 'dermatitis')

    def test_multi_part_question_answers_both_topics(self):
        result = self.bot.reply('what causes psoriasis and how can I treat it?')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn(self.bot.knowledge.get('psoriasis', 'causes'), result['reply'])
        self.assertIn(self.bot.knowledge.get('psoriasis', 'management'), result['reply'])
        self.assertEqual(self.bot.conversation.get('last_knowledge_topics'), ['causes', 'management'])

    def test_new_condition_replaces_the_knowledge_topic(self):
        self.bot.reply('what causes psoriasis?')
        self.bot.reply('what is rosacea?')
        result = self.bot.reply('and treatment?')
        self.assertIn(self.bot.knowledge.get('rosacea', 'management'), result['reply'])
        self.assertNotIn('Psoriasis', result['reply'])

    def test_simple_question_with_an_explicit_topic_does_not_ignore_it(self):
        result = self.bot.reply('explain in simple words what causes eczema')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn('Dermatitis', result['reply'])
        self.assertEqual(self.bot.conversation.get('last_knowledge_topics'), ['causes'])

    def test_self_report_with_a_question_records_only_what_the_user_said(self):
        message = 'I have an itchy rash on my arm for two weeks, what causes it?'
        result = self.bot.reply(message)
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn(message, self.bot.conversation.get('symptoms'))
        self.assertEqual(self.bot.conversation.get('duration'), message)
        self.assertIsNone(self.bot.conversation.get('classification'))

    def test_duration_number_needs_a_unit_before_it_is_saved(self):
        self.bot.reply('my rash is itchy on my arm')
        result = self.bot.reply('2')
        self.assertEqual(result['intent'], 'invalid_duration')
        self.assertIsNone(self.bot.conversation.get('duration'))
        self.assertEqual(result['followUps'], ['2 days', '2 weeks', '2 months'])
        result = self.bot.reply('2 weeks')
        self.assertEqual(self.bot.conversation.get('duration'), '2 weeks')
        self.assertIn('medication', result['reply'])

    def test_repeated_unclear_answers_offer_a_way_to_skip(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        self.bot.reply('123')
        result = self.bot.reply('456')
        self.assertIn("say 'skip'", result['reply'])
        self.assertIsNone(self.bot.conversation.get('medication'))
        self.bot.reply('skip')
        self.assertEqual(self.bot.conversation.get('medication'), 'unknown')

    def test_yes_to_medication_asks_what_was_used(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        result = self.bot.reply('yes')
        self.assertIn('What did you use', result['reply'])
        self.assertIsNone(self.bot.conversation.get('medication'))
        self.assertEqual(self.bot.conversation.get('pending_question'), 'medication')
        self.bot.reply('I used a cream')
        self.assertEqual(self.bot.conversation.get('medication'), 'I used a cream')

    def test_no_after_knowledge_does_not_claim_no_medication(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        self.bot.reply('what is psoriasis?')
        self.bot.reply('no')
        self.assertIsNone(self.bot.conversation.get('medication'))

    def test_voluntary_medication_report_does_not_replace_rash_duration(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        self.bot.reply('what is psoriasis?')
        previous_duration = self.bot.conversation.get('duration')
        message = 'I used a cream yesterday'
        result = self.bot.reply(message)
        self.assertEqual(result['intent'], 'medication')
        self.assertEqual(self.bot.conversation.get('medication'), message)
        self.assertEqual(self.bot.conversation.get('duration'), previous_duration)

    def test_photo_requests_only_return_the_upload_action(self):
        result = self.bot.reply('can i uplod an image?')
        self.assertEqual(result['action'], 'upload_image')
        self.assertIn('Choose photo', result['reply'])
        self.assertFalse(self.bot.conversation.get('image_uploaded'))
        self.assertIn('Choose photo', self.bot.reply('idk')['reply'])

    def test_simplifying_a_photo_result_does_not_request_symptoms(self):
        self.photo()
        result = self.bot.reply('make it simpler')
        self.assertEqual(result['intent'], 'simple_explanation')
        self.assertIn('Atopic Dermatitis', result['reply'])
        self.assertIn('not a confirmed diagnosis', result['reply'])
        self.assertNotIn('what skin problem', result['reply'])
        self.assertIsNone(self.bot.conversation.get('pending_question'))

    def test_confidence_questions_explain_the_existing_photo(self):
        self.photo()
        for message in ['are you sure?', 'can I trust this result?', 'how confident are you?']:
            with self.subTest(message=message):
                result = self.bot.reply(message)
                self.assertEqual(result['intent'], 'image_explanation')
                self.assertIn('88.0%', result['reply'])
                self.assertIn('not a confirmed diagnosis', result['reply'])
                self.assertIsNone(result['action'])
        self.assertEqual(self.bot.image_classifier.calls, 1)

    def test_rejected_photo_is_not_explained_using_an_older_result(self):
        self.photo()
        self.bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
        self.photo()
        result = self.bot.reply('what does this result mean?')
        self.assertEqual(result['intent'], 'image_explanation')
        self.assertIn('latest photo', result['reply'])
        self.assertNotIn('Atopic Dermatitis', result['reply'])
        self.assertIsNone(result['confidence'])
        self.assertEqual(result['action'], 'upload_image')

    def test_care_question_after_rejection_does_not_use_an_older_photo(self):
        self.photo()
        self.bot.reply('what causes it?')
        self.bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
        self.photo()
        result = self.bot.reply('how can I treat it?')
        self.assertIn("couldn't reliably classify the latest photo", result['reply'])
        self.assertNotIn(self.bot.knowledge.get('dermatitis', 'management'), result['reply'])

    def test_pronoun_after_uncertainty_still_refers_to_the_last_knowledge_answer(self):
        self.photo()
        self.bot.reply('what causes it?')
        self.bot.reply('idk')
        result = self.bot.reply('what does that mean?')
        self.assertEqual(result['intent'], 'simple_explanation')
        self.assertIn('Short version', result['reply'])

    def test_explicit_condition_can_be_discussed_after_a_normal_skin_result(self):
        self.bot.image_classifier.result.update(predicted_class='normal_skin', condition='No Condition Detected')
        self.photo()
        self.bot.reply('what is psoriasis?')
        result = self.bot.reply('and treatment?')
        self.assertIn(self.bot.knowledge.get('psoriasis', 'management'), result['reply'])

    def test_initial_photo_rejection_still_has_a_useful_followup(self):
        self.bot.image_classifier.result = {'status': 'rejected', 'reason': 'no_skin_detected'}
        self.photo()
        result = self.bot.reply('what do you think about that photo?')
        self.assertIn("couldn't detect enough skin", result['reply'])
        self.assertIsNone(self.bot.conversation.get('classification'))

    def test_summary_distinguishes_unprovided_and_unknown_fields(self):
        self.bot.reply('my rash is itchy')
        self.bot.reply('idk')
        result = self.bot.reply('what do you remember?')
        self.assertEqual(result['intent'], 'conversation_summary')
        self.assertIn('my rash is itchy', result['reply'])
        self.assertIn('Affected area: unknown', result['reply'])
        self.assertIn('How long: not provided', result['reply'])
        self.assertNotIn('Last classified photo:', result['reply'])

    def test_summary_retains_photo_uncertainty(self):
        self.photo()
        result = self.bot.reply('sumarize our conversation')
        self.assertIn('Atopic Dermatitis', result['reply'])
        self.assertIn('not a confirmed diagnosis', result['reply'])
        self.assertIn('Skin symptoms: not provided', result['reply'])

    def test_pause_and_resume_keep_information_without_forcing_questions(self):
        self.bot.reply('my rash is itchy')
        self.bot.reply('stop asking questions')
        result = self.bot.reply('my arm')
        self.assertEqual(self.bot.conversation.get('location'), 'my arm')
        self.assertNotIn('How long', result['reply'])
        self.assertIsNone(self.bot.conversation.get('pending_question'))
        result = self.bot.reply('continue screening')
        self.assertIn('How long', result['reply'])
        self.assertEqual(self.bot.conversation.get('pending_question'), 'duration')
        self.assertEqual(result['followUps'], ['Two days', 'Two weeks', "I'm not sure"])

    def test_simple_explanation_of_a_question_keeps_its_answer_choices(self):
        self.bot.reply('my rash is itchy on my arm')
        result = self.bot.reply('what do you mean?')
        self.assertIn('how long', result['reply'])
        self.assertEqual(result['followUps'], ['Two days', 'Two weeks', "I'm not sure"])
        self.bot.reply('idk')
        self.assertEqual(self.bot.conversation.get('duration'), 'unknown')

    def test_correction_updates_multiple_fields_and_excludes_negated_locations(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        result = self.bot.reply('actually not my arm, my left leg for three weeks')
        self.assertEqual(result['intent'], 'correction')
        self.assertEqual(self.bot.conversation.get('location'), 'left leg')
        self.assertEqual(self.bot.conversation.get('duration'), 'three weeks')
        self.assertIn('duration', result['reply'])

    def test_duration_correction_excludes_the_old_negated_value(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        self.bot.reply('actually three days, not two weeks')
        self.assertEqual(self.bot.conversation.get('duration'), 'three days')

    def test_medication_correction_can_record_a_negative_answer(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        self.bot.reply('I used a cream')
        self.bot.reply('actually I did not use any cream')
        self.assertEqual(self.bot.conversation.get('medication'), 'none')

    def test_correcting_treatment_duration_does_not_change_skin_problem_duration(self):
        self.bot.reply('my rash is itchy on my arm for two weeks')
        previous_duration = self.bot.conversation.get('duration')
        self.bot.reply('actually I used a cream for three days')
        self.assertEqual(self.bot.conversation.get('duration'), previous_duration)
        self.assertEqual(self.bot.conversation.get('medication'), 'actually I used a cream for three days')

    def test_medication_question_does_not_claim_a_specific_prescription(self):
        self.photo()
        result = self.bot.reply('which cream should I use?')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn("can't choose a medicine or dose", result['reply'])
        self.assertIsNone(self.bot.conversation.get('medication'))


if __name__ == '__main__':
    unittest.main()
