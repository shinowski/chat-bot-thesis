"""Run with: python -B -m unittest test_image_integration -v."""

import io
import contextlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from werkzeug.datastructures import FileStorage

from app import create_app
from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.dataset import Dataset
from model.flow_manager import FlowManager
from model.image_classifier import ImageClassifier, ImageClassifierError
from model.knowledge_base import KnowledgeBase
from model.semantic_chatbot import SemanticChatbot


class FakeImageClassifier:
    def __init__(self):
        self.calls = 0
        self.result = {
            "status": "ok", "predicted_class": "atopic_dermatitis",
            "condition": "Atopic Dermatitis", "confidence": 0.88,
            "all_probabilities": {"atopic_dermatitis": 0.88},
            "gradcam": "data:image/png;base64,fixture",
        }

    def predict(self, image):
        self.calls += 1
        return dict(self.result)


class FakeTextClassifier:
    def predict(self, message):
        return ("emergency" if "swallowing" in message else "symptom"), 0.9


def make_bot():
    root = Path(__file__).resolve().parent
    bot = SemanticChatbot.__new__(SemanticChatbot)
    bot.data = Dataset(root / "data/intents.json").load()
    bot.conversation = Conversation()
    bot.classifier = FakeTextClassifier()
    bot.context = ContextIntent()
    bot.flow = FlowManager()
    bot.knowledge = KnowledgeBase(root / "data/knowledge_base.json")
    bot.image_classifier = FakeImageClassifier()
    return bot


class ImageChatTests(unittest.TestCase):
    def setUp(self):
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.bot = make_bot()
        self.app = create_app(self.bot)
        self.addCleanup(self.app.extensions["chat_history"].db.close)
        self.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = self.app.test_client()

    def upload(self, client=None, **fields):
        return (client or self.client).post("/predict", data={
            "image": (io.BytesIO(b"image-bytes"), "skin.png"), **fields,
        })

    def test_upload_returns_classification_and_heatmap(self):
        result = self.upload().get_json()
        self.assertEqual(result["intent"], "image_classification")
        self.assertEqual(result["classification"], "dermatitis")
        self.assertEqual(result["imageResult"]["predicted_class"], "atopic_dermatitis")
        self.assertEqual(result["confidence"], 0.88)
        self.assertTrue(result["imageResult"]["gradcam"].startswith("data:image/png;base64,"))

    def test_all_six_classes_are_accepted_and_mapped(self):
        expected = {
            "atopic_dermatitis": "dermatitis", "contact_dermatitis": "dermatitis",
            "lichen_planus": "lichen planus", "normal_skin": "normal_skin",
            "psoriasis": "psoriasis", "rosacea": "rosacea",
        }
        for raw, normalized in expected.items():
            with self.subTest(raw=raw):
                self.bot.image_classifier.result["predicted_class"] = raw
                self.assertEqual(self.upload().get_json()["classification"], normalized)

    def test_rejections_leave_image_step_incomplete(self):
        for reason in ["no_skin_detected", "out_of_scope", "low_confidence", "inconclusive", "default"]:
            with self.subTest(reason=reason):
                bot = make_bot()
                bot.image_classifier.result = {"status": "rejected", "reason": reason}
                result = bot.reply("", FileStorage(filename="skin.png"))
                self.assertEqual(result["intent"], "image_rejected")
                self.assertFalse(bot.conversation.get("image_uploaded"))
                self.assertIsNone(bot.conversation.get("classification"))

    def test_inconclusive_result_does_not_claim_the_photo_file_is_unreadable(self):
        self.bot.image_classifier.result = {'status': 'rejected', 'reason': 'inconclusive'}
        result = self.upload().get_json()
        self.assertIn("couldn't reach a reliable result", result['reply'])
        self.assertNotIn("couldn't read this image", result['reply'])

    def test_unavailable_image_service_returns_retry_message(self):
        with patch.object(self.bot.image_classifier, "predict", side_effect=ImageClassifierError("offline")):
            result = self.upload()
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.get_json()["intent"], "image_error")

    def test_caption_updates_screening_before_classification(self):
        result = self.upload(message="I have an itchy rash on my arm for two weeks").get_json()
        self.assertEqual(result["intent"], "image_classification")
        self.assertIn("medication", result["reply"])

    def test_emergency_caption_takes_priority_over_image(self):
        result = self.upload(message="my tongue is getting bigger and swallowing is becoming difficult").get_json()
        self.assertEqual(result["intent"], "emergency")
        self.assertEqual(self.bot.image_classifier.calls, 0)

    def test_json_text_messages_are_supported(self):
        result = self.client.post("/predict", json={"message": "my skin is itchy"}).get_json()
        self.assertEqual(result["intent"], "symptom")
        self.assertIn("Where", result["reply"])

    def test_two_clients_do_not_share_screening(self):
        self.client.post("/predict", json={"message": "my skin is itchy"})
        other = self.app.test_client()
        result = other.post("/predict", json={"message": "my skin is itchy"}).get_json()
        self.assertEqual(result["intent"], "symptom")

    def test_chats_in_one_client_are_independent(self):
        self.upload(conversation_id="one")
        result = self.client.post("/predict", json={
            "message": "what is it?", "conversation_id": "two",
        }).get_json()
        self.assertIn("Which of these conditions", result["reply"])
        result = self.client.post("/predict", json={
            "message": "what is it?", "conversation_id": "one",
        }).get_json()
        self.assertNotIn("Which of these conditions", result["reply"])

    def test_normal_skin_clears_previous_disease_context(self):
        self.bot.reply("", FileStorage(filename="skin.png"))
        self.bot.image_classifier.result["predicted_class"] = "normal_skin"
        self.bot.reply("", FileStorage(filename="skin.png"))
        self.assertIsNone(self.bot.conversation.get("knowledge_disease"))

    def test_invalid_confidence_is_not_stored(self):
        for value in [float("nan"), float("inf"), -1, 2, None]:
            with self.subTest(value=value):
                self.assertFalse(self.bot.receive_classification("psoriasis", value)["success"])
                self.assertIsNone(self.bot.conversation.get("classification"))

    def test_medication_no_completes_screening(self):
        for message in ["my skin is itchy", "my arm", "two weeks", "mild", "no"]:
            result = self.bot.reply(message)
        self.assertEqual(self.bot.conversation.get("medication"), "none")
        self.assertIn("upload", result["reply"])

    def test_location_only_message_is_not_stored_as_a_symptom(self):
        self.bot.reply("my arm")
        self.assertEqual(self.bot.conversation.get("symptoms"), [])
        self.assertEqual(self.bot.conversation.get("location"), "my arm")

    def test_invalid_payload_returns_400(self):
        for payload in [["bad"], {"message": 123}, {"conversation_id": "../bad"}]:
            self.assertEqual(self.client.post("/predict", json=payload).status_code, 400)

    def test_photo_request_can_interrupt_every_screening_stage(self):
        for stage in ["symptom", "location", "duration", "severity", "medication", "image_upload", None]:
            with self.subTest(stage=stage):
                self.assertEqual(self.bot.context.resolve("image_upload", "can I send picture?", self.bot.conversation, stage), "image_request")
        result = self.bot.reply("can I send picture?")
        self.assertIn("Yes", result["reply"])
        self.assertFalse(self.bot.conversation.get("image_uploaded"))
        self.assertIsNone(result["confidence"])

    def test_location_in_photo_request_is_kept(self):
        self.bot.reply("i have a skin rashesh")
        result = self.bot.reply("in my arm can i send picture?")
        self.assertEqual(result["intent"], "image_request")
        self.assertIn("arm", self.bot.conversation.get("location"))
        self.assertIsNone(self.bot.conversation.get("duration"))
        self.assertFalse(self.bot.conversation.get("image_uploaded"))

    def test_uncertainty_variants_leave_medication_unknown_and_advance(self):
        for message in ["i dont know", "im not sure", "can't tell", "I'm not sure.", "I’m not sure?", "skip"]:
            with self.subTest(message=message):
                bot = make_bot()
                for answer in ["my skin is itchy", "my arm", "two weeks"]:
                    bot.reply(answer)
                result = bot.reply(message)
                self.assertEqual(result["intent"], "uncertain_answer")
                self.assertIsNone(bot.conversation.get("severity"))
                self.assertEqual(bot.conversation.get("medication"), "unknown")
                self.assertIn("upload", result["reply"])

    def test_uncertainty_does_not_invent_medication_use(self):
        for answer in ["my skin is itchy", "my arm", "two weeks", "mild"]:
            self.bot.reply(answer)
        self.bot.reply("im not sure")
        self.assertEqual(self.bot.conversation.get("medication"), "unknown")

    def test_severity_can_be_updated_after_uncertainty(self):
        for answer in ["my skin is itchy", "my arm", "two weeks", "im not sure", "moderate"]:
            self.bot.reply(answer)
        self.assertEqual(self.bot.conversation.get("severity"), "moderate")

    def test_image_reference_uses_last_result_without_marking_a_new_upload(self):
        self.bot.reply("", FileStorage(filename="skin.png"))
        calls = self.bot.image_classifier.calls
        result = self.bot.reply("how about this")
        self.assertEqual(result["intent"], "image_followup")
        self.assertIn("Atopic Dermatitis", result["reply"])
        self.assertIn("attach", result["reply"])
        self.assertEqual(self.bot.image_classifier.calls, calls)

    def test_latest_photo_replaces_previous_result_context(self):
        self.bot.reply("", FileStorage(filename="skin.png"))
        self.bot.image_classifier.result.update(predicted_class="psoriasis", condition="Psoriasis")
        self.bot.reply("", FileStorage(filename="skin.png"))
        result = self.bot.reply("what about this?")
        self.assertIn("Psoriasis", result["reply"])
        self.assertNotIn("Atopic Dermatitis", result["reply"])

    def test_photo_caption_does_not_ask_for_the_attached_image_again(self):
        self.bot.reply("", FileStorage(filename="skin.png"))
        result = self.bot.reply("how about this", FileStorage(filename="second.png"))
        self.assertEqual(result["intent"], "image_classification")
        self.assertNotIn("To check another photo", result["reply"])

    def test_overridden_model_confidence_is_kept_separate(self):
        with patch.object(self.bot.classifier, "predict", return_value=("image_upload", 0.919)):
            result = self.bot.reply("can I send picture?")
        self.assertEqual(result["intent"], "image_request")
        self.assertIsNone(result["confidence"])
        self.assertIsNone(result["confidenceSource"])
        self.assertEqual(result["predictedIntent"], "image_upload")
        self.assertEqual(result["modelConfidence"], 0.919)

    def test_no_severity_question_or_options_during_screening(self):
        for message in ["hello", "my skin is itchy", "my arm", "two weeks", "no"]:
            result = self.bot.reply(message)
            self.assertNotIn("How severe", result["reply"])
            self.assertNotIn("moderate", result["reply"].lower())
            self.assertNotIn("severe", result["reply"].lower())
            self.assertFalse({"Mild", "Moderate", "Severe"} & set(result["followUps"]))
        self.assertEqual(self.bot.flow.get_expected_intent(self.bot.conversation), "image_upload")
        self.assertIsNone(self.bot.conversation.get("severity"))

    def test_image_request_returns_upload_action_without_questions(self):
        for message in ["i want to send an image", "can I send picture?", "I'd like to upload a photo", "let me attach a pic", "in my arm can i send picture?"]:
            with self.subTest(message=message):
                result = self.client.post("/predict", json={"message": message, "conversation_id": "request"}).get_json()
                self.assertEqual(result["intent"], "image_request")
                self.assertEqual(result["action"], "upload_image")
                self.assertEqual(result["followUps"], [])
                self.assertIn("Choose photo", result["reply"])
                self.assertNotIn("How severe", result["reply"])

    def test_image_upload_before_any_screening_answers(self):
        result = self.upload().get_json()
        self.assertEqual(result["intent"], "image_classification")
        self.assertNotIn("severe", result["reply"].lower())

    def test_matched_model_confidence_and_image_confidence_remain_available(self):
        with patch.object(self.bot.classifier, "predict", return_value=("symptom", 0.59)):
            result = self.bot.reply("i have a skin rashesh")
        self.assertEqual(result["confidence"], 0.59)
        self.assertEqual(result["confidenceSource"], "intent_model")
        image = self.bot.reply("", FileStorage(filename="skin.png"))
        self.assertEqual(image["confidenceSource"], "image_model")

    def test_result_explanation_handles_normal_skin(self):
        self.bot.image_classifier.result.update(predicted_class="normal_skin", condition="No Condition Detected")
        self.bot.reply("", FileStorage(filename="skin.png"))
        result = self.bot.reply("What does this result mean?")
        self.assertEqual(result["intent"], "image_explanation")
        self.assertIn("No Condition Detected", result["reply"])
        self.assertNotIn("Which of these conditions", result["reply"])

    def test_emergency_still_takes_priority_over_photo_requests(self):
        result = self.bot.reply("can't breathe, can i send a photo?")
        self.assertEqual(result["intent"], "emergency")
        self.assertEqual(result["followUps"], [])

    def test_oversized_upload_returns_friendly_error(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 100
        result = self.upload()
        self.assertEqual(result.status_code, 413)
        self.assertEqual(result.get_json()["intent"], "image_rejected")


class ImageTransportTests(unittest.TestCase):
    def upload(self):
        return FileStorage(stream=io.BytesIO(b"binary-image\x00\xff"), filename="skin.png")

    def test_multipart_forwards_image_bytes(self):
        response = io.BytesIO(json.dumps({"status": "ok"}).encode())
        with patch("model.image_classifier.urlopen", return_value=response) as send:
            ImageClassifier().predict(self.upload())
        request = send.call_args.args[0]
        self.assertIn(b'name="image"', request.data)
        self.assertIn(b"binary-image\x00\xff", request.data)

    def test_http_400_preserves_rejection_reason(self):
        error = HTTPError("http://test", 400, "bad", {}, io.BytesIO(b'{"status":"rejected","reason":"out_of_scope"}'))
        with patch("model.image_classifier.urlopen", side_effect=error):
            self.assertEqual(ImageClassifier().predict(self.upload())["reason"], "out_of_scope")

    def test_bad_response_and_connection_errors_are_handled(self):
        for error in [URLError("offline"), TimeoutError()]:
            with patch("model.image_classifier.urlopen", side_effect=error):
                with self.assertRaises(ImageClassifierError):
                    ImageClassifier().predict(self.upload())
        for body in [b"not json", b"[]", b'{"status":"unexpected"}']:
            with patch("model.image_classifier.urlopen", return_value=io.BytesIO(body)):
                with self.assertRaises(ImageClassifierError):
                    ImageClassifier().predict(self.upload())


if __name__ == "__main__":
    unittest.main()
