"""Regression cases for imperfect English, shorthand, and truthful slot storage."""

import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from model.text_understanding import has_duration_answer, normalize_message, no_medication
from test_image_integration import make_bot


def prepare_bot(stage):
    bot = make_bot()
    if stage != "symptom":
        bot.conversation.add_symptom("rash")
    if stage in {"duration", "medication", "image_explanation"}:
        bot.conversation.set("location", "arm")
    if stage in {"medication", "image_explanation"}:
        bot.conversation.set("duration", "two weeks")
    if stage == "image_explanation":
        bot.conversation.set("medication", "none")
        bot.receive_classification("psoriasis", 0.95)
        bot.conversation.set("image_condition", "Psoriasis")
        bot.conversation.set("knowledge_disease", "psoriasis")
    return bot


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def test_imperfect_english_corpus(self):
        cases = json.loads((Path(__file__).parent / "eval/language_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(message=case["message"]):
                bot = prepare_bot(case["stage"])
                result = bot.reply(case["message"])
                self.assertEqual(result["intent"], case["intent"])

    def test_classifier_receives_cleaned_text(self):
        bot = make_bot()
        with patch.object(bot.classifier, "predict", return_value=("image_upload", 0.9)) as predict:
            bot.reply("can i sent pictuer?")
        predict.assert_called_once_with("can i send picture?")

    def test_original_location_and_duration_are_retained(self):
        bot = prepare_bot("location")
        bot.reply("on my left sholder")
        bot.reply("2wks")
        self.assertEqual(bot.conversation.get("location"), "on my left sholder")
        self.assertEqual(bot.conversation.get("duration"), "2wks")

    def test_combined_answer_preserves_all_provided_information(self):
        bot = make_bot()
        message = "my skn is icthy on my amrs for 2wks"
        result = bot.reply(message)
        self.assertIn(message, bot.conversation.get("symptoms"))
        self.assertEqual(bot.conversation.get("location"), message)
        self.assertEqual(bot.conversation.get("duration"), message)
        self.assertIn("medication", result["reply"])

    def test_no_medication_with_missing_apostrophes_and_wrong_verb(self):
        for message in ["i havent use any creem", "I havnt applied anything", "no meds", "I didnt use anything"]:
            with self.subTest(message=message):
                bot = prepare_bot("medication")
                result = bot.reply(message)
                self.assertEqual(result["intent"], "medication")
                self.assertEqual(bot.conversation.get("medication"), "none")

    def test_mixed_medication_answer_keeps_actual_usage(self):
        for message in ["no tablets but i used creem", "no cream, just ointment", "i have not used cream and i used ointment"]:
            with self.subTest(message=message):
                bot = prepare_bot("medication")
                bot.reply(message)
                self.assertEqual(bot.conversation.get("medication"), message)

    def test_medication_date_does_not_replace_condition_duration(self):
        bot = prepare_bot("medication")
        message = "ive use a creem for 2days"
        self.assertEqual(bot.reply(message)["intent"], "medication")
        self.assertEqual(bot.conversation.get("medication"), message)
        self.assertEqual(bot.conversation.get("duration"), "two weeks")

    def test_medicine_names_and_strengths_are_preserved(self):
        bot = prepare_bot("medication")
        message = "I used Tacrolimus 0.1% ointment yesterday"
        bot.reply(message)
        self.assertEqual(bot.conversation.get("medication"), message)
        self.assertEqual(bot.conversation.get("duration"), "two weeks")
        self.assertIn("tacrolimus 0.1%", normalize_message(message))

    def test_question_about_cream_is_not_recorded_as_using_it(self):
        bot = prepare_bot("medication")
        result = bot.reply("can i use this creem?")
        self.assertEqual(result["intent"], "knowledge_question")
        self.assertIsNone(bot.conversation.get("medication"))

    def test_uncertainty_shorthand_has_the_same_meaning(self):
        for message in ["idk", "i dunno", "not shure", "IM NOT SURE!!"]:
            with self.subTest(message=message):
                bot = prepare_bot("duration")
                result = bot.reply(message)
                self.assertEqual(result["intent"], "uncertain_answer")
                self.assertEqual(bot.conversation.get("duration"), "unknown")

    def test_polite_small_replies_interrupt_field_validation(self):
        for message, intent in [("hellooo", "greeting"), ("hi!!", "greeting"), ("tnx alot", "thanks"), ("bye!!!", "goodbye"), ("reset!", "reset")]:
            with self.subTest(message=message):
                self.assertEqual(prepare_bot("location").reply(message)["intent"], intent)

    def test_body_parts_use_consistent_recognition_and_storage(self):
        for message in ["my forehead", "left ankle", "on my wrist", "my forhead", "on my sholder"]:
            with self.subTest(message=message):
                bot = prepare_bot("location")
                self.assertEqual(bot.reply(message)["intent"], "location")
                self.assertEqual(bot.conversation.get("location"), message)

    def test_negated_upload_request_does_not_open_picker(self):
        for message in ["I dont want to uplod a phto", "I cant send a pictuer", "I wont upload an image"]:
            with self.subTest(message=message):
                result = prepare_bot("location").reply(message)
                self.assertNotEqual(result["intent"], "image_request")
                self.assertIsNone(result["action"])

    def test_claiming_an_upload_does_not_complete_image_step(self):
        bot = prepare_bot("medication")
        bot.reply("no meds")
        bot.reply("I already sent a picture")
        self.assertFalse(bot.conversation.get("image_uploaded"))
        self.assertIsNone(bot.conversation.get("classification"))

    def test_declined_photo_is_respected_even_when_model_predicts_upload(self):
        bot = make_bot()
        with patch.object(bot.classifier, "predict", return_value=("image_upload", 0.96)):
            result = bot.reply("I dont want to uplod a phto")
        self.assertEqual(result["intent"], "image_declined")
        self.assertIn("continue in text", result["reply"])
        self.assertIsNone(result["action"])
        self.assertFalse(bot.conversation.get("image_uploaded"))

    def test_emergency_spelling_stays_highest_priority(self):
        result = prepare_bot("duration").reply("i cant breath can i sent pictuer")
        self.assertEqual(result["intent"], "emergency")
        self.assertIsNone(result["action"])

    def test_disease_spelling_and_short_answers_keep_knowledge_context(self):
        bot = prepare_bot("medication")
        result = bot.reply("whats psoraisis")
        self.assertEqual(result["intent"], "knowledge_question")
        self.assertEqual(bot.conversation.get("knowledge_disease"), "psoriasis")
        self.assertEqual(bot.reply("is it contagous?")["intent"], "knowledge_question")
        self.assertEqual(bot.reply("rosasea please")["intent"], "knowledge_question")
        self.assertEqual(bot.conversation.get("knowledge_disease"), "rosacea")

    def test_correction_with_misspelled_body_part(self):
        bot = prepare_bot("duration")
        result = bot.reply("sorry i ment my sholder")
        self.assertEqual(result["intent"], "correction")
        self.assertEqual(bot.conversation.get("location"), "shoulder")

    def test_weak_unsupported_guess_asks_for_clarification(self):
        bot = make_bot()
        with patch.object(bot.classifier, "predict", return_value=("symptom", 0.18)):
            result = bot.reply("asdfjkl")
        self.assertEqual(result["intent"], "clarification")
        self.assertEqual(bot.conversation.get("symptoms"), [])
        self.assertIsNone(result["confidence"])

    def test_known_symptom_does_not_require_high_model_confidence(self):
        bot = make_bot()
        with patch.object(bot.classifier, "predict", return_value=("symptom", 0.18)):
            result = bot.reply("my rash is icthy")
        self.assertEqual(result["intent"], "symptom")

    def test_normalization_is_idempotent_and_preserves_numbers(self):
        for message in ["I’m not shure!!", "can i sent pictuer?", "2.5wks", "Tacrolimus 0.1% ointment", "i havent use creem", "I already sent an image"]:
            with self.subTest(message=message):
                cleaned = normalize_message(message)
                self.assertEqual(normalize_message(cleaned), cleaned)
        self.assertIn("2.5 weeks", normalize_message("2.5wks"))
        self.assertEqual(normalize_message("I already sent an image"), "i already sent an image")
        self.assertFalse(no_medication("i used cream"))

    def test_duration_requires_a_timeframe_not_an_incidental_shorthand(self):
        for message in ['lala mo', 'banana month', 'show me', 'since banana', 'mo', '123']:
            with self.subTest(message=message):
                self.assertFalse(has_duration_answer(message))
        for message in ['2mo', '2.5wks', 'a month', 'several days', 'a couple of weeks', 'last week',
                        'yesterday', 'since Monday', 'since March', 'since 2024', 'since I was a child',
                        'since I was little', 'Years now', 'for a while']:
            with self.subTest(message=message):
                self.assertTrue(has_duration_answer(message))

    def test_incidental_month_alias_does_not_fill_duration_from_another_answer(self):
        bot = make_bot()
        bot.reply('my rash is itchy lala mo')
        self.assertIsNone(bot.conversation.get('duration'))

    def test_newly_recognized_symptoms_and_body_parts_are_not_blocked(self):
        for message in ['my eyebrow is swollen', 'I have a wart', 'there is a sore on my calf', 'my collarbone feels numb']:
            with self.subTest(message=message):
                bot = make_bot()
                bot.reply(message)
                self.assertIn(message, bot.conversation.get('symptoms'))


if __name__ == "__main__":
    unittest.main()
