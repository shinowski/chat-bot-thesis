"""Expected condition course must not become a reported patient duration."""

import json
import unittest

from app import create_app
from model.knowledge_base import KnowledgeBase, is_course_question
from test_image_integration import make_bot
from test_photo_topic_context import accepted_photo


class CourseQuestionTests(unittest.TestCase):
    def test_reported_contact_followup_answers_course_and_preserves_facts(self):
        for question in ['how long this usually last?', 'How long does it last?',
                         'When will it clear up?', 'How much time does it take to heal',
                         'What is the usual duration?', 'How soon will it get better?']:
            bot = make_bot()
            bot.reply('My rash is on my elbow for 1 hour')
            bot.reply('I used a cream')
            accepted_photo(bot, 'contact_dermatitis')
            before = {key: bot.conversation.get(key) for key in ['symptoms', 'location', 'duration', 'medication']}
            result = bot.reply(question)
            self.assertEqual(result['intent'], 'knowledge_question', question)
            self.assertIn('days to weeks', result['reply'], question)
            self.assertIn('not a personal recovery deadline', result['reply'])
            self.assertEqual(result['treatmentInfo']['topic'], 'course')
            self.assertTrue(result['treatmentInfo']['sources'])
            self.assertEqual(result['sourceImageId'], 'fixture-photo')
            self.assertEqual(bot.conversation.get('last_knowledge_topics'), ['course'])
            for key, value in before.items():
                self.assertEqual(bot.conversation.get(key), value, (question, key))

    def test_predicted_time_in_a_question_is_never_saved_as_observed_onset(self):
        bot = make_bot()
        report = 'My rash is on my arm for two weeks'
        bot.reply(report)
        bot.reply('Tell me about contact dermatitis')
        for question in ['Will my rash last 3 weeks?', "I don't know how long this will last"]:
            self.assertEqual(bot.reply(question)['intent'], 'knowledge_question')
            self.assertEqual(bot.conversation.get('duration'), report)
            self.assertEqual(bot.conversation.get('symptoms'), [report])

    def test_all_known_conditions_have_a_course_response_without_an_individual_deadline(self):
        knowledge = KnowledgeBase()
        self.assertEqual(set(knowledge.data), set(knowledge.courses['conditions']))
        for key in knowledge.data:
            bot = make_bot()
            question = 'How long does ' + knowledge.data[key]['name'] + ' usually last?'
            result = bot.reply(question)
            self.assertEqual(result['intent'], 'knowledge_question', key)
            self.assertIn(knowledge.get(key, 'course'), result['reply'], key)
            self.assertIsNone(bot.conversation.get('duration'))
            if key != 'normal_skin':
                self.assertTrue(result['treatmentInfo']['sources'], key)

    def test_unknown_or_rejected_condition_cannot_get_an_invented_timeline(self):
        bot = make_bot()
        result = bot.reply('How long will this rash last?')
        self.assertNotIn('treatmentInfo', result)
        self.assertIsNone(bot.conversation.get('duration'))
        bot.conversation.invalidate_image_result('Not reliable.')
        self.assertIn("couldn't reliably classify", bot.reply('How long will this last?')['reply'])
        self.assertNotIn('treatmentInfo', bot.reply('How long until the skin heals?'))

    def test_course_subject_switch_inherits_course_and_not_a_cure_promise(self):
        bot = make_bot()
        bot.reply('How long does contact dermatitis usually last?')
        result = bot.reply('and rosacea')
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'rosacea')
        self.assertEqual(bot.conversation.get('last_knowledge_topics'), ['course'])
        self.assertIn('long-term', result['reply'])

    def test_medication_use_duration_and_past_onset_are_separate_questions(self):
        for text in ['How long should I use a cream to heal this?',
                     'How long do I take the medicine?', 'I used a cream for three days',
                     'How long have I had it?', "I don't know how long I've had it",
                     'My rash has lasted for two days']:
            self.assertFalse(is_course_question(text), text)
        bot = make_bot()
        bot.reply('My rash is on my arm for two weeks')
        self.assertEqual(bot.reply("I don't know how long I've had it")['intent'], 'uncertain_answer')
        self.assertEqual(bot.conversation.get('duration'), 'unknown')

    def test_warning_signs_still_take_priority_over_course_questions(self):
        self.assertEqual(make_bot().reply('How long will this last? I cannot breathe')['intent'], 'emergency')

    def test_course_and_care_question_retains_both_sets_of_sources(self):
        reply = make_bot().reply('How long will contact dermatitis last and what can I do?')
        self.assertIn('days to weeks', reply['reply'])
        self.assertIn('General care:', reply['reply'])
        self.assertEqual(reply['treatmentInfo']['topic'], 'course_and_management')
        urls = [source['url'] for source in reply['treatmentInfo']['sources']]
        self.assertTrue(any('111.wales.nhs.uk' in url for url in urls))
        self.assertTrue(any('aad.org' in url for url in urls))

    def test_course_sources_and_topic_survive_history_restore(self):
        app = create_app(make_bot(), history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        client.post('/predict', json={'message': 'Tell me about contact dermatitis'})
        response = client.post('/predict', json={'message': 'how long this usually last?'}).get_json()
        self.assertEqual(response['messages'][1]['treatmentInfo']['topic'], 'course')
        row = app.extensions['chat_history'].db.execute('SELECT state FROM conversations').fetchone()
        restored = make_bot()
        restored.conversation.restore(json.loads(row['state']))
        self.assertIn('days to weeks', restored.reply('Explain simply')['reply'])
        self.assertEqual(restored.conversation.get('last_knowledge_topics'), ['course'])


if __name__ == '__main__':
    unittest.main()
