"""Photo-conditioned information and named-condition discussion keep their origin."""

import io
import json
import unittest

from werkzeug.datastructures import FileStorage

from app import create_app
from test_chat_history import PNG
from test_image_integration import make_bot


def accepted_photo(bot, label='atopic_dermatitis'):
    bot.image_classifier.result['predicted_class'] = label
    bot.image_classifier.result['condition'] = label.replace('_', ' ').title()
    bot.reply('', FileStorage(filename='fixture.png'))
    bot.conversation.set('classification_image_id', 'fixture-photo')


class PhotoTopicContextTests(unittest.TestCase):
    def test_every_photo_word_recovers_photo_care_after_a_named_topic_change(self):
        for word in ['photo', 'photos', 'picture', 'pictures', 'image', 'images', 'pic', 'pics', 'result', 'results']:
            bot = make_bot()
            accepted_photo(bot)
            bot.reply('Tell me about rosacea')
            reply = bot.reply('Treatment for my ' + word)
            self.assertEqual(reply['treatmentInfo']['condition_key'], 'atopic_dermatitis', word)
            self.assertEqual(reply['sourceImageId'], 'fixture-photo', word)
            self.assertIn('photo model\'s screening suggestion', reply['reply'])
            self.assertEqual(bot.conversation.get('knowledge_origin'), 'photo_screening')
            self.assertEqual(bot.image_classifier.calls, 1)

    def test_rejected_plural_photo_reference_never_reuses_named_treatment(self):
        for word in ['images', 'photos', 'pictures', 'pics', 'results']:
            bot = make_bot()
            accepted_photo(bot)
            bot.conversation.invalidate_image_result('Not reliable.')
            bot.reply('Tell me about rosacea')
            reply = bot.reply('Treatment for my ' + word)
            self.assertIn("couldn't reliably classify", reply['reply'])
            self.assertNotIn('treatmentInfo', reply)
            self.assertNotIn('sourceImageId', reply)

    def test_same_named_condition_does_not_implicitly_attribute_general_care_to_photo(self):
        bot = make_bot()
        accepted_photo(bot)
        for message in ['Treatment options for atopic dermatitis', 'Is it treatable?']:
            reply = bot.reply(message)
            self.assertEqual(reply['treatmentInfo']['condition_key'], 'atopic_dermatitis')
            self.assertEqual(bot.conversation.get('knowledge_origin'), 'named_condition')
            self.assertNotIn('sourceImageId', reply)
            self.assertNotIn('For the photo model', reply['reply'])
        photo = bot.reply('Treatment options for these pics')
        self.assertEqual(photo['sourceImageId'], 'fixture-photo')
        self.assertEqual(bot.conversation.get('knowledge_origin'), 'photo_screening')
        self.assertEqual(bot.reply('Is it treatable?')['sourceImageId'], 'fixture-photo')

    def test_different_named_condition_and_own_photo_receive_a_context_note(self):
        bot = make_bot()
        accepted_photo(bot)
        reply = bot.reply('Treatment for rosacea in my photo')
        self.assertIn("latest photo's screening match was Atopic Dermatitis", reply['reply'])
        self.assertIn('general information about Rosacea', reply['reply'])
        self.assertEqual(reply['treatmentInfo']['condition_key'], 'rosacea')
        self.assertNotIn('sourceImageId', reply)
        self.assertEqual(bot.image_knowledge_disease(), 'atopic_dermatitis')
        self.assertEqual(bot.conversation.get('knowledge_origin'), 'named_condition')

    def test_named_condition_after_rejected_photo_remains_educational(self):
        bot = make_bot()
        bot.conversation.invalidate_image_result('Not reliable.')
        reply = bot.reply('Treatment for rosacea in my images')
        self.assertIn('latest photo could not be classified reliably', reply['reply'])
        self.assertEqual(reply['treatmentInfo']['condition_key'], 'rosacea')
        self.assertNotIn('sourceImageId', reply)

    def test_general_photo_education_does_not_introduce_an_unrelated_personal_result(self):
        bot = make_bot()
        accepted_photo(bot)
        reply = bot.reply('What does rosacea look like in photos?')
        self.assertNotIn("latest photo's screening match was", reply['reply'])
        self.assertNotIn('sourceImageId', reply)

    def test_normal_match_care_does_not_retain_a_named_disease(self):
        bot = make_bot()
        accepted_photo(bot, 'normal_skin')
        bot.reply('Tell me about rosacea')
        reply = bot.reply('Treatment for my pictures')
        self.assertEqual(reply['treatmentInfo']['condition_key'], 'normal_skin')
        self.assertEqual(reply['treatmentInfo']['clinician_options'], [])
        self.assertEqual(reply['sourceImageId'], 'fixture-photo')
        self.assertIsNone(bot.conversation.get('knowledge_disease'))
        self.assertEqual(bot.reply('Is it treatable?')['treatmentInfo']['condition_key'], 'normal_skin')

    def test_named_diagnosis_question_changes_discussion_origin_without_relabeling_photo(self):
        bot = make_bot()
        accepted_photo(bot)
        bot.reply('Do I have atopic dermatitis?')
        self.assertEqual(bot.conversation.get('knowledge_origin'), 'named_condition')
        self.assertNotIn('sourceImageId', bot.reply('Is it treatable?'))
        self.assertEqual(bot.conversation.get('classification'), 'dermatitis')

    def test_origin_survives_saved_history_and_a_new_photo_starts_new_photo_context(self):
        bot = make_bot()
        app = create_app(bot, history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        photo = client.post('/predict', data={'image': (io.BytesIO(PNG), 'skin.png')}).get_json()
        source = photo['messages'][0]['id']
        for text in ['Treatment options for atopic dermatitis', 'Is it treatable?']:
            self.assertNotIn('sourceImageId', client.post('/predict', json={'message': text}).get_json())
        row = app.extensions['chat_history'].db.execute('SELECT state FROM conversations').fetchone()
        restored = make_bot()
        restored.conversation.restore(json.loads(row['state']))
        self.assertNotIn('sourceImageId', restored.reply('Is it treatable?'))
        self.assertEqual(restored.reply('Treatment for my images')['sourceImageId'], source)
        accepted_photo(restored, 'psoriasis')
        self.assertEqual(restored.reply('Is it treatable?')['treatmentInfo']['condition_key'], 'psoriasis')
        restored.conversation.invalidate_image_result('Rejected.')
        self.assertIsNone(restored.conversation.get('knowledge_origin'))

    def test_photo_doctor_question_uses_photo_condition_and_warnings_still_win(self):
        bot = make_bot()
        accepted_photo(bot)
        bot.reply('Tell me about rosacea')
        reply = bot.reply('When should I see a doctor for my photos?')
        self.assertIn('For Atopic Dermatitis:', reply['reply'])
        self.assertNotIn('For Rosacea:', reply['reply'])
        self.assertEqual(bot.reply('Treatment for my pictures, I cannot breathe')['intent'], 'emergency')

    def test_explaining_photo_restores_its_context_for_a_bare_followup(self):
        bot = make_bot()
        accepted_photo(bot)
        bot.reply('Tell me about rosacea')
        explanation = bot.reply('What do you think about my photos?')
        self.assertEqual(explanation['intent'], 'image_explanation')
        self.assertEqual(bot.conversation.get('knowledge_disease'), 'atopic_dermatitis')
        restored = make_bot()
        restored.conversation.restore(bot.conversation.data)
        reply = restored.reply('Is it treatable?')
        self.assertEqual(reply['treatmentInfo']['condition_key'], 'atopic_dermatitis')
        self.assertEqual(reply['sourceImageId'], 'fixture-photo')

    def test_explaining_rejection_cannot_make_a_named_condition_a_photo_result(self):
        bot = make_bot()
        bot.conversation.invalidate_image_result('Rejected.')
        bot.reply('Tell me about rosacea')
        self.assertEqual(bot.reply('What do you think about my photos?')['intent'], 'image_explanation')
        self.assertIsNone(bot.conversation.get('knowledge_disease'))
        self.assertIsNone(bot.conversation.get('knowledge_origin'))
        self.assertNotIn('treatmentInfo', bot.reply('Is it treatable?'))


if __name__ == '__main__':
    unittest.main()
