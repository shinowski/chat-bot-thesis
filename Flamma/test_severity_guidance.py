"""Condition-aware severity education and user descriptions, not clinical grading."""
import json
import unittest
from app import create_app
from model.knowledge_base import topic_requests
from model.severity_support import severity_question
from test_image_integration import make_bot
from test_photo_topic_context import accepted_photo


class SeverityGuidanceTests(unittest.TestCase):
    def start(self):
        bot = make_bot()
        result = bot.reply('how can i know how severe my psoriasis is')
        return bot, result

    def test_original_question_gets_specific_factors_and_a_relevant_question(self):
        for question in ['how can i know how severe my psoriasis is',
                         'How severe is my psoriasis?', 'Is my psoriasis mild or severe?',
                         'How can I assess psoriasis severity?', 'how do i check my psoriasis severety?']:
            with self.subTest(question=question):
                bot = make_bot()
                result = bot.reply(question)
                self.assertEqual(result['intent'], 'severity_guidance')
                self.assertIn('plaque thickness', result['reply'])
                self.assertIn('whole handprint', result['reply'])
                self.assertIn('Which body areas', result['reply'])
                self.assertNotIn('is a chronic', result['reply'])
                self.assertEqual(result['treatmentInfo']['topic'], 'severity')
                self.assertTrue(result['treatmentInfo']['sources'])
                self.assertIsNone(result['confidence'])
                self.assertIsNone(bot.conversation.get('classification'))
                self.assertIsNone(bot.conversation.get('severity'))

    def test_personal_followups_remember_descriptions_without_assigning_grade(self):
        bot, _ = self.start()
        response = bot.reply('Both elbows')
        self.assertIn('how much skin', response['reply'])
        response = bot.reply('about two handprints')
        self.assertIn('sleep', response['reply'])
        response = bot.reply('It affects my sleep')
        self.assertIn('joint', response['reply'])
        response = bot.reply('No joint symptoms')
        self.assertIn('Both elbows', response['reply'])
        self.assertIn('about two handprints', response['reply'])
        self.assertIn('You described disruption', response['reply'])
        self.assertIn('not a clinical severity grade', response['reply'])
        self.assertNotIn('You reported new joint symptoms', response['reply'])
        self.assertFalse(bot.conversation.get('severity_discussion')['active'])
        self.assertIsNone(bot.conversation.get('severity'))
        self.assertIsNone(bot.conversation.get('location'))
        self.assertIsNone(bot.conversation.get('classification'))
        self.assertIn('about two handprints', bot.reply('Summarize our conversation')['reply'])

    def test_new_joint_symptoms_get_assessment_advice_not_arthritis_diagnosis(self):
        bot, _ = self.start()
        for text in ['Both knees', 'two handprints', 'No effect on daily activities']:
            bot.reply(text)
        response = bot.reply('Yes, new joint stiffness')
        self.assertIn('Arrange a clinician assessment', response['reply'])
        self.assertIn('cannot determine whether these are psoriatic arthritis', response['reply'])
        self.assertIsNone(bot.conversation.get('classification'))

    def test_unknown_answers_advance_without_inventing_details(self):
        bot, _ = self.start()
        for _ in range(4):
            result = bot.reply("I'm not sure")
            self.assertEqual(result['intent'], 'severity_guidance')
        answers = bot.conversation.get('severity_discussion')['answers']
        self.assertEqual(set(answers.values()), {'unknown'})
        self.assertNotIn('You reported new joint symptoms', result['reply'])

    def test_coverage_ambiguity_or_out_of_range_needs_clarification(self):
        for estimate in ['two or ten handprints', '200 handprints', '-2 handprints']:
            bot, _ = self.start()
            bot.reply('My elbows')
            result = bot.reply(estimate)
            self.assertIn('one rough estimate', result['reply'])
            self.assertNotIn('extent', bot.conversation.get('severity_discussion')['answers'])
            self.assertEqual(bot.conversation.get('severity_discussion')['pending'], 'extent')

    def test_courtesy_does_not_answer_the_question(self):
        bot, _ = self.start()
        bot.reply('Thanks')
        self.assertEqual(bot.conversation.get('severity_discussion')['answers'], {})
        result = bot.reply('My elbows')
        self.assertEqual(result['intent'], 'severity_guidance')

    def test_different_question_interrupts_and_preserves_screening_facts(self):
        bot = make_bot()
        bot.reply('my rash is itchy on my arm for two weeks')
        before = dict(bot.conversation.data)
        bot.reply('How severe is my psoriasis?')
        result = bot.reply('What causes rosacea?')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertIn('Rosacea', result['reply'])
        self.assertFalse(bot.conversation.get('severity_discussion')['active'])
        self.assertEqual(bot.conversation.get('location'), before['location'])
        self.assertEqual(bot.conversation.get('duration'), before['duration'])

    def test_other_condition_does_not_get_psoriasis_coverage_or_joint_rules(self):
        bot = make_bot()
        result = bot.reply('How severe is my rosacea?')
        self.assertNotIn('about 1%', result['reply'])
        for text in ['My cheeks', 'a few small patches', 'No effect on daily activities', 'No eye symptoms']:
            result = bot.reply(text)
        self.assertNotIn('psoriatic arthritis', result['reply'])
        self.assertFalse(bot.conversation.get('severity_discussion')['active'])

    def test_topic_switch_restarts_discussion_for_new_condition(self):
        bot, _ = self.start()
        bot.reply('My elbows')
        result = bot.reply('and rosacea')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'rosacea')
        self.assertEqual(bot.conversation.get('severity_discussion')['answers'], {})

    def test_named_condition_choice_keeps_requested_severity_topic(self):
        bot = make_bot()
        result = bot.reply('How severe is psoriasis or rosacea?')
        self.assertEqual(result['intent'], 'condition_clarification')
        result = bot.reply('second one')
        self.assertEqual(result['treatmentInfo']['topic'], 'severity')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'rosacea')

    def test_generic_question_does_not_invent_psoriasis(self):
        result = make_bot().reply('How severe is my skin condition?')
        self.assertEqual(result['intent'], 'severity_guidance')
        self.assertNotIn('For psoriasis:', result['reply'])
        self.assertIsNone(result['treatmentInfo']['condition_key'])

    def test_photo_context_keeps_screening_uncertainty_and_provenance(self):
        bot = make_bot()
        accepted_photo(bot, 'psoriasis')
        result = bot.reply('How severe is it?')
        self.assertIn('not a confirmed diagnosis', result['reply'])
        self.assertEqual(result['sourceImageId'], bot.conversation.get('classification_image_id'))
        self.assertEqual(result['treatmentInfo']['condition_key'], 'psoriasis')

    def test_rejected_photo_does_not_reuse_old_severity_context(self):
        bot, _ = self.start()
        bot.reply('my elbows')
        bot.conversation.invalidate_image_result('Latest photo was rejected.')
        result = bot.reply('How severe is it?')
        self.assertIsNone(result['treatmentInfo']['condition_key'])
        self.assertNotIn('For psoriasis:', result['reply'])

    def test_photo_reference_uses_actual_photo_after_a_named_topic_change(self):
        bot = make_bot()
        accepted_photo(bot, 'psoriasis')
        bot.reply('What causes rosacea?')
        result = bot.reply('How severe is my photo result?')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'psoriasis')
        self.assertIn('not a confirmed diagnosis', result['reply'])
        self.assertEqual(result['sourceImageId'], 'fixture-photo')

    def test_rejected_photo_reference_does_not_borrow_a_named_condition(self):
        bot = make_bot()
        bot.conversation.invalidate_image_result('Not reliable.')
        bot.reply('What is psoriasis?')
        result = bot.reply('How severe is my photo result?')
        self.assertIn("couldn't reliably classify", result['reply'])
        self.assertNotIn('treatmentInfo', result)
        self.assertIsNone(bot.conversation.get('severity_discussion'))

    def test_emergency_overrides_discussion_and_stops_questions(self):
        bot, _ = self.start()
        result = bot.reply('I cannot breathe')
        self.assertEqual(result['intent'], 'emergency')
        self.assertFalse(bot.conversation.get('severity_discussion')['active'])
        self.assertGreaterEqual(len(result['followUps']), 3)
        self.assertNotIn('Continue severity questions', result['followUps'])

    def test_reset_clears_and_stop_preserves_discussion_as_user_descriptions(self):
        bot, _ = self.start()
        bot.reply('My elbows')
        result = bot.reply('Stop severity questions')
        self.assertIn('stopped', result['reply'])
        self.assertFalse(bot.conversation.get('severity_discussion')['active'])
        bot.reply('reset')
        self.assertIsNone(bot.conversation.get('severity_discussion'))

    def test_summary_simplification_and_persisted_state(self):
        bot, _ = self.start()
        simple = bot.reply('Explain simply')
        self.assertIn('A small patch can still matter', simple['reply'])
        clone = make_bot()
        clone.conversation.restore(json.loads(json.dumps(bot.conversation.data)))
        result = clone.reply('My elbows')
        self.assertEqual(result['intent'], 'severity_guidance')
        self.assertIn('My elbows', clone.conversation.get('severity_discussion')['answers']['sites'])

    def test_api_sources_and_chat_state_are_separate(self):
        app = create_app(make_bot(), history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        result = client.post('/predict', json={'message': 'How severe is my psoriasis?', 'conversation_id': 'one'}).get_json()
        self.assertEqual(result['messages'][-1]['treatmentInfo']['topic'], 'severity')
        result = client.post('/predict', json={'message': 'My elbows', 'conversation_id': 'two'}).get_json()
        self.assertNotEqual(result['intent'], 'severity_guidance')

    def test_severity_report_remains_distinct_from_assessment_question(self):
        self.assertFalse(severity_question('I have severe psoriasis'))
        self.assertFalse(severity_question('the itching is severe'))
        self.assertFalse(severity_question("I don't know how severe it is"))
        self.assertNotIn('severity', topic_requests('the itching is severe'))


class AllConditionSeverityTests(unittest.TestCase):
    def test_every_covered_condition_has_specific_content_and_questions(self):
        bot = make_bot()
        for disease, data in bot.knowledge.data.items():
            with self.subTest(disease=disease):
                self.assertIn(disease, bot.knowledge.severities)
                entry = bot.knowledge.severities[disease]
                self.assertTrue(entry['sources'])
                self.assertIn('fields', entry)
                result = make_bot().reply('How severe is my ' + data['name'] + '?')
                self.assertEqual(result['intent'], 'severity_guidance')
                self.assertEqual(result['treatmentInfo']['condition_key'], disease)
                self.assertIn(entry['overview'], result['reply'])
                self.assertIsNone(result['confidence'])

    def test_every_disease_completes_its_own_followups(self):
        details = {'dermatitis': 'No known type or trigger',
                   'atopic_dermatitis': 'It comes and goes in flares',
                   'contact_dermatitis': 'A new soap touched the area',
                   'lichen_planus': 'No nail changes or scalp hair loss',
                   'rosacea': 'No eye symptoms', 'hives': 'One welt fades within hours; new welts for two weeks',
                   'psoriasis': 'No joint symptoms'}
        for disease, data in make_bot().knowledge.data.items():
            with self.subTest(disease=disease):
                bot = make_bot()
                bot.reply('How severe is my ' + data['name'] + '?')
                for message in ['My arms', 'a few small patches', 'No effect on daily activities']:
                    result = bot.reply(message)
                    self.assertEqual(result['intent'], 'severity_guidance')
                if disease in details:
                    result = bot.reply(details[disease])
                    self.assertEqual(result['intent'], 'severity_guidance')
                session = bot.conversation.get('severity_discussion')
                self.assertFalse(session['active'])
                self.assertIn('not a clinical severity grade', result['reply'])
                self.assertIsNone(bot.conversation.get('classification'))
                self.assertIsNone(bot.conversation.get('severity'))

    def test_condition_specific_questions_are_not_psoriasis_clones(self):
        expected = {'dermatitis': ('type', 'clinician'), 'atopic_dermatitis': ('flares', 'flares'),
                    'contact_dermatitis': ('exposure', 'new product'), 'lichen_planus': ('special_sites', 'hair loss'),
                    'rosacea': ('eyes', 'gritty'), 'hives': ('pattern', 'one welt')}
        for disease, (field, phrase) in expected.items():
            with self.subTest(disease=disease):
                bot = make_bot()
                result = bot.reply('How severe is my '+bot.knowledge.data[disease]['name']+'?')
                self.assertNotIn('about 1%', result['reply'])
                for text in ['My arms', 'a few small patches', 'No effect on daily activities']:
                    result = bot.reply(text)
                self.assertEqual(bot.conversation.get('severity_discussion')['pending'], field)
                self.assertIn(phrase, result['reply'])
                self.assertNotIn('joint', result['reply'])

    def test_condition_aliases_use_the_right_severity_profile(self):
        for name, key in [('eczema', 'dermatitis'), ('atopic eczema', 'atopic_dermatitis'),
                          ('urticaria', 'hives'), ('lichen planus', 'lichen_planus')]:
            with self.subTest(name=name):
                result = make_bot().reply('How can I know how severe my '+name+' is?')
                self.assertEqual(result['treatmentInfo']['condition_key'], key)

    def test_unknown_can_skip_every_condition_specific_followup(self):
        for disease, data in make_bot().knowledge.data.items():
            with self.subTest(disease=disease):
                bot = make_bot()
                bot.reply('How severe is my '+data['name']+'?')
                for _ in bot.knowledge.severities[disease]['fields']:
                    result = bot.reply("I'm not sure")
                    self.assertEqual(result['intent'], 'severity_guidance')
                self.assertFalse(bot.conversation.get('severity_discussion')['active'])
                self.assertEqual(set(bot.conversation.get('severity_discussion')['answers'].values()), {'unknown'})

    def test_normal_photo_is_not_a_disease_or_a_severity_grade(self):
        bot = make_bot()
        accepted_photo(bot, 'normal_skin')
        result = bot.reply('How severe is my photo result?')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'normal_skin')
        self.assertIn('not a disease severity grade', result['reply'])
        self.assertIn('does not confirm', result['reply'])
        self.assertIsNone(bot.conversation.get('knowledge_disease'))

    def test_new_rosacea_eye_warning_interrupts_at_any_step(self):
        for warning in ['My vision is blurry', 'My eyes hurt', 'I am sensitive to light']:
            with self.subTest(warning=warning):
                bot = make_bot()
                bot.reply('How severe is my rosacea?')
                result = bot.reply(warning)
                self.assertEqual(result['intent'], 'medical_attention')
                self.assertIn('urgent medical advice', result['reply'])
                self.assertGreaterEqual(len(result['followUps']), 3)
                self.assertNotIn('Continue severity questions', result['followUps'])
                self.assertFalse(bot.conversation.get('severity_discussion')['active'])

    def test_negated_eye_warning_and_educational_question_are_not_current_emergency(self):
        for text in ['No eye pain or blurred vision', 'Can rosacea cause blurred vision?']:
            bot = make_bot()
            bot.reply('How severe is my rosacea?')
            result = bot.reply(text)
            self.assertNotIn(result['intent'], {'medical_attention', 'emergency'})

    def test_hives_faintness_interrupts_before_text_inference(self):
        bot = make_bot()
        bot.reply('How severe are my hives?')
        from unittest.mock import patch
        with patch.object(bot.classifier, 'predict', side_effect=AssertionError('Warning must precede inference')):
            result = bot.reply('I feel faint')
        self.assertEqual(result['intent'], 'emergency')
        self.assertGreaterEqual(len(result['followUps']), 3)
        self.assertNotIn('Continue severity questions', result['followUps'])

    def test_photo_subtypes_remain_distinct_in_severity_discussion(self):
        for disease in ['atopic_dermatitis', 'contact_dermatitis', 'lichen_planus', 'psoriasis', 'rosacea']:
            with self.subTest(disease=disease):
                bot = make_bot()
                accepted_photo(bot, disease)
                result = bot.reply('How severe is it?')
                self.assertEqual(result['treatmentInfo']['condition_key'], disease)
                self.assertEqual(result['sourceImageId'], 'fixture-photo')


if __name__ == '__main__':
    unittest.main()
