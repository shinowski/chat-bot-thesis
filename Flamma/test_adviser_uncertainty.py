"""Integration checks with simulated image results; not image accuracy tests."""
import unittest
from pathlib import Path
from werkzeug.datastructures import FileStorage
from test_image_integration import make_bot
from model.expert_system import ExpertSystem


class IntegrationBoundaryTests(unittest.TestCase):
    def test_mislabelled_success_with_low_score_cannot_establish_condition(self):
        for score in [0, .1, .5499]:
            bot = make_bot()
            bot.reply('', FileStorage(filename='skin.png'))
            bot.image_classifier.result['confidence'] = score
            result = bot.reply('', FileStorage(filename='skin.png'))
            self.assertEqual(result['intent'], 'image_rejected')
            self.assertEqual(result['imageResult']['reason'], 'low_confidence')
            self.assertIsNone(bot.conversation.get('classification'))
            self.assertIsNone(bot.conversation.get('image_knowledge_key'))
            self.assertNotIn('treatmentInfo', result)
            followup = bot.reply('Treatment options for this photo')
            self.assertNotIn('treatmentInfo', followup)
            self.assertIn("couldn't reliably classify", followup['reply'])

    def test_service_uncertainty_flag_overrides_high_score(self):
        bot = make_bot()
        bot.image_classifier.result.update(confidence=.99, is_confident=False)
        result = bot.reply('', FileStorage(filename='skin.png'))
        self.assertEqual(result['intent'], 'image_rejected')
        self.assertIsNone(bot.conversation.get('classification'))

    def test_boundary_score_is_accepted_with_screening_wording(self):
        bot = make_bot()
        bot.image_classifier.result['confidence'] = .55
        result = bot.reply('', FileStorage(filename='skin.png'))
        self.assertEqual(result['intent'], 'image_classification')
        self.assertIn('not a confirmed diagnosis', result['reply'])

    def test_boolean_is_not_a_probability(self):
        self.assertFalse(make_bot().receive_classification('psoriasis', True)['success'])

    def test_expert_system_rejects_nonfinite_confidence(self):
        expert = ExpertSystem(Path(__file__).parent/'data/expert_rules.json')
        for value in [float('nan'), float('inf'), -float('inf')]:
            result = expert.evaluate({'classification': 'psoriasis', 'classification_confidence': value})
            self.assertEqual(result['status'], 'invalid_confidence')


if __name__ == '__main__':
    unittest.main()
