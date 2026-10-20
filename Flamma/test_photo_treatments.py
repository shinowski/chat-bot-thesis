"""Treatment guidance uses accepted photo labels, never inferred diagnoses."""

import io
import json
import unittest
from unittest.mock import patch

from werkzeug.datastructures import FileStorage

from app import create_app
from model.image_classifier import ImageClassifierError
from test_image_integration import make_bot
from test_conversation_followups import patient_data
from test_safety_and_reliability import PNG


PHOTO_CLASSES = ['atopic_dermatitis', 'contact_dermatitis', 'lichen_planus',
                 'psoriasis', 'rosacea', 'normal_skin']


class PhotoTreatmentTests(unittest.TestCase):
    def photo(self, bot, condition):
        bot.image_classifier.result.update(
            predicted_class=condition, condition=bot.knowledge.data[condition]['name'])
        return bot.reply('', FileStorage(stream=io.BytesIO(b'fixture'), filename='skin.png'))

    def test_every_supported_class_shows_its_own_care_and_sources_on_upload(self):
        for condition in PHOTO_CLASSES:
            with self.subTest(condition=condition):
                bot = make_bot()
                result = self.photo(bot, condition)
                self.assertEqual(result['intent'], 'image_classification')
                self.assertIn('not a confirmed diagnosis', result['reply'])
                self.assertIn(bot.knowledge.treatment_text(condition), result['reply'])
                self.assertEqual(result['treatmentInfo']['condition_key'], condition)
                self.assertTrue(result['treatmentInfo']['sources'])
                self.assertIn('Treatment options for this photo', result['followUps'])
                self.assertEqual(bot.image_classifier.calls, 1)

    def test_treatment_followup_uses_photo_without_another_inference(self):
        for condition in PHOTO_CLASSES:
            with self.subTest(condition=condition):
                bot = make_bot()
                self.photo(bot, condition)
                before = patient_data(bot)
                with patch.object(bot.classifier, 'predict', return_value=('location', .99)):
                    result = bot.reply('Treatment options for this photo')
                self.assertEqual(result['intent'], 'knowledge_question')
                self.assertEqual(result['treatmentInfo']['condition_key'], condition)
                self.assertIn(bot.knowledge.treatment_text(condition), result['reply'])
                self.assertEqual(patient_data(bot), before)
                self.assertEqual(bot.image_classifier.calls, 1)
                self.assertIsNone(result['action'])

    def test_explicit_photo_request_restores_photo_context_after_another_condition(self):
        bot = make_bot()
        self.photo(bot, 'contact_dermatitis')
        bot.reply('What is psoriasis?')
        result = bot.reply('How can I treat the rash in this photo?')
        self.assertEqual(result['intent'], 'knowledge_question')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'contact_dermatitis')
        self.assertIn('not a confirmed diagnosis', result['reply'])
        self.assertNotIn('General information about Psoriasis', result['reply'])

    def test_explicit_named_treatment_does_not_overwrite_the_photo_class(self):
        bot = make_bot()
        self.photo(bot, 'atopic_dermatitis')
        result = bot.reply('How is rosacea treated?')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'rosacea')
        self.assertEqual(bot.image_knowledge_disease(), 'atopic_dermatitis')
        self.assertEqual(bot.reply('Treatment options for this photo')['treatmentInfo']['condition_key'], 'atopic_dermatitis')

    def test_raw_label_controls_guidance_even_if_display_name_is_inconsistent(self):
        bot = make_bot()
        bot.image_classifier.result.update(predicted_class='contact_dermatitis', condition='Atopic Dermatitis')
        result = bot.reply('', FileStorage(filename='skin.png'))
        self.assertEqual(result['treatmentInfo']['condition_key'], 'contact_dermatitis')
        self.assertIn('closest match is Contact Dermatitis', result['reply'])
        self.assertEqual(bot.image_knowledge_disease(), 'contact_dermatitis')

    def test_new_accepted_photo_replaces_treatment_context(self):
        bot = make_bot()
        self.photo(bot, 'psoriasis')
        self.photo(bot, 'rosacea')
        result = bot.reply('and treatment?')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'rosacea')
        self.assertNotIn(bot.knowledge.treatment_text('psoriasis'), result['reply'])

    def test_rejected_or_unavailable_new_photo_cannot_reuse_old_treatment(self):
        for unavailable in [False, True]:
            bot = make_bot()
            self.photo(bot, 'psoriasis')
            if unavailable:
                with patch.object(bot.image_classifier, 'predict', side_effect=ImageClassifierError('offline')):
                    failed = bot.reply('', FileStorage(filename='new.png'))
            else:
                bot.image_classifier.result = {'status': 'rejected', 'reason': 'low_confidence'}
                failed = bot.reply('', FileStorage(filename='new.png'))
            self.assertNotIn('treatmentInfo', failed)
            result = bot.reply('Treatment options for this photo')
            self.assertNotIn('treatmentInfo', result)
            self.assertIn("couldn't reliably classify", result['reply'])
            self.assertIsNone(bot.conversation.get('image_knowledge_key'))

    def test_failed_photo_question_does_not_attach_an_unrelated_named_treatment(self):
        bot = make_bot()
        bot.conversation.invalidate_image_result('Unclear photo')
        bot.reply('How is psoriasis treated?')
        result = bot.reply('Treatment options for this photo')
        self.assertNotIn('treatmentInfo', result)
        self.assertNotIn('sourceImageId', result)
        self.assertIn("couldn't reliably classify", result['reply'])

    def test_unsupported_class_has_no_treatment(self):
        bot = make_bot()
        bot.image_classifier.result.update(predicted_class='hives', condition='Hives')
        result = bot.reply('', FileStorage(filename='skin.png'))
        self.assertEqual(result['intent'], 'image_rejected')
        self.assertNotIn('treatmentInfo', result)

    def test_normal_skin_does_not_recommend_disease_medicine(self):
        bot = make_bot()
        self.photo(bot, 'normal_skin')
        result = bot.reply('How can I treat it?')
        self.assertEqual(result['treatmentInfo']['clinician_options'], [])
        self.assertIn('No disease-specific medication', result['reply'])
        self.assertIsNone(bot.conversation.get('knowledge_disease'))

    def test_warning_report_stops_treatment_reply_and_photo_processing(self):
        bot = make_bot()
        self.photo(bot, 'psoriasis')
        result = bot.reply('What treatment should I use? I cannot breathe', FileStorage(filename='new.png'))
        self.assertEqual(result['intent'], 'emergency')
        self.assertNotIn('treatmentInfo', result)
        self.assertEqual(bot.image_classifier.calls, 1)

    def test_saved_photo_treatment_and_subtype_survive_restore(self):
        bot = make_bot()
        app = create_app(bot, history_path=':memory:')
        self.addCleanup(app.extensions['chat_history'].db.close)
        client = app.test_client()
        result = client.post('/predict', data={'image': (io.BytesIO(PNG), 'skin.png')}).get_json()
        source = result['messages'][0]['id']
        detail = client.get('/api/conversations/default').get_json()
        self.assertEqual(detail['messages'][1]['treatmentInfo']['condition_key'], 'atopic_dermatitis')
        self.assertEqual(detail['messages'][1]['sourceImageId'], source)
        with client.session_transaction() as session:
            owner = session['client_id']
        state = json.loads(app.extensions['chat_history'].get(owner, 'default')['state'])
        restored = make_bot()
        restored.conversation.restore(state)
        result = restored.reply('Treatment options for this photo')
        self.assertEqual(result['treatmentInfo']['condition_key'], 'atopic_dermatitis')
        self.assertEqual(result['sourceImageId'], source)


if __name__ == '__main__':
    unittest.main()
