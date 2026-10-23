import unittest
from eval.adviser.evaluate_images import BACKEND, summarize


class ImageDenominatorTests(unittest.TestCase):
    def test_rejected_images_stay_in_full_test_denominator(self):
        rows = [dict(label='a',predicted='a',accepted=True),
                dict(label='a',predicted='a',accepted=False),
                dict(label='b',predicted='a',accepted=True),
                dict(label='unsupported',predicted='a',accepted=False)]
        result = summarize(rows,['a','b'])
        self.assertEqual(result['raw_supported_classifier']['samples'],3)
        self.assertAlmostEqual(result['raw_supported_classifier']['accuracy'],2/3)
        self.assertEqual(result['accepted_supported_classifier']['accuracy'],.5)
        self.assertAlmostEqual(result['supported_end_to_end_correct_fraction'],1/3)
        self.assertAlmostEqual(result['supported_coverage'],2/3)
        self.assertEqual(result['unsupported_rejection_fraction'],1)
        self.assertEqual(result['per_class_gate_results']['a']['rejected'],1)

    def test_all_rejected_is_no_accepted_accuracy(self):
        result=summarize([dict(label='a',predicted='a',accepted=False)],['a'])
        self.assertIsNone(result['accepted_supported_classifier']['accuracy'])
        self.assertEqual(result['supported_end_to_end_correct_fraction'],0)
        self.assertEqual(result['supported_coverage'],0)

    def test_backend_path_resolves_to_existing_active_checkpoint(self):
        self.assertTrue((BACKEND/'models/resnet50_skin_finale_oe.pth').is_file())

if __name__=='__main__':
    unittest.main()
