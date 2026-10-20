from copy import copy
from math import isfinite
from pathlib import Path
import random
import re
from model.knowledge_base import KnowledgeBase, is_disease_overview_question, topic_requests, management_style, is_course_question
from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.flow_manager import FlowManager
from model.dataset import Dataset
from model.dialogue import concise, correction_updates, dialogue_act, is_medication_question, is_self_report, is_medication_report, medication_report_parts
from model.image_classifier import ImageClassifier, ImageClassifierError
from model.config import intent_model_path
from model.safety import GENERAL_CARE_GUIDANCE, SAFETY_RESPONSES, is_care_question, safety_intent, safety_response
from model.chat_support import confirmation_kind
from model.question_clarification import knowledge_choice_index, clarification_request, screening_choice_answer, bare_product_answer
from model.dialogue import SPECIFIC_MEDICINES, looks_like_question
from model.text_understanding import (
    LOCATION_WORDS, SYMPTOM_WORDS, SEVERITY_WORDS, PHOTO_REFERENCES,
    has_duration_answer, has_screening_evidence, message_words, no_medication, normalize_message, symptom_mentions,
)


class SemanticChatbot:

    def receive_classification(self, classification, confidence):


        allowed_diseases = {
            "dermatitis",
            "lichen planus",
            "lichen_planus",
            "psoriasis",
            "rosacea",
            "normal_skin",
        }

        if classification is None:
            return {
                "success": False,
                "message": "No classification result was provided."
            }

        normalized_classification = str(classification).lower().strip()
        knowledge_key = normalized_classification.replace(' ', '_')
        normalized_classification = {
            "atopic_dermatitis": "dermatitis",
            "contact_dermatitis": "dermatitis",
        }.get(normalized_classification, normalized_classification)

        if normalized_classification not in allowed_diseases:
            return {
                "success": False,
                "message": "The classification result is not supported by Flamma."
            }

        # Normalize Lichen Planus naming
        if normalized_classification == "lichen_planus":
            normalized_classification = "lichen planus"

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return {
                "success": False,
                "message": "The classification confidence is invalid."
            }

        if not isfinite(confidence) or confidence < 0.0 or confidence > 1.0:
            return {
                "success": False,
                "message": "The classification confidence must be between 0 and 1."
            }

        self.conversation.set(
            "classification",
            normalized_classification
        )

        self.conversation.set(
            "classification_confidence",
            confidence
        )

        self.conversation.set(
            "image_uploaded",
            True
        )
        self.conversation.set("last_image_status", "ok")
        self.conversation.set("last_image_feedback", None)
        self.conversation.set('image_knowledge_key', knowledge_key)
        self.conversation.set("last_knowledge_topics", [])
        self.conversation.set('last_management_style', None)

        return {
            "success": True,
            "classification": normalized_classification,
            "confidence": confidence
        }

    def __init__(self, image_classifier=None):
        from model.intent_classifier import IntentClassifier

        project_dir = Path(__file__).resolve().parents[1]
        # Load dataset for chatbot responses
        self.dataset = Dataset(project_dir / "data/intents.json")
        self.data = self.dataset.load()

        # Conversation memory
        self.conversation = Conversation()

        # Semantic intent classifier
        self.classifier = IntentClassifier()
        self.classifier.load(intent_model_path())

        # Context and flow management
        self.flow = FlowManager()
        self.knowledge = KnowledgeBase(project_dir / "data/knowledge_base.json")
        self.context = ContextIntent(self.knowledge)
        self.image_classifier = image_classifier or ImageClassifier()

        print("Semantic chatbot initialized successfully!")

    def new_conversation(self):
        """Share the loaded models, while keeping screening state independent."""
        chatbot = copy(self)
        chatbot.conversation = Conversation()
        return chatbot

    def get_image_response(self, image):
        try:
            result = self.image_classifier.predict(image)
        except ImageClassifierError:
            feedback = "I couldn't reach the image classifier. Please try the image upload again shortly."
            self.conversation.invalidate_image_result(feedback)
            return dict(reply=feedback, intent="image_error", confidence=None, followUps=[],
                        imageResult={"status": "rejected", "reason": "unavailable"})
        if result["status"] == "rejected":
            reasons = {
                "no_skin_detected": "I couldn't detect enough skin in this image. Please upload a clear, close-up photo of the affected area.",
                "out_of_scope": "This image falls outside the image model's supported conditions. I couldn't classify it reliably.",
                "low_confidence": "The image model isn't confident enough to classify this photo. Please try a clearer photo with good lighting.",
                "inconclusive": "The image model couldn't reach a reliable result from this photo. Please try a clear close-up of the affected skin in good lighting.",
            }
            feedback = reasons.get(result.get("reason"), "I couldn't read this image. Please upload a JPG, PNG, or WebP photo.")
            self.conversation.invalidate_image_result(feedback)
            return {
                "reply": feedback,
                "intent": "image_rejected",
                "confidence": None,
                "followUps": [],
                "imageResult": result,
            }

        accepted = self.receive_classification(
            result.get("predicted_class"), result.get("confidence")
        )
        if not accepted["success"]:
            self.conversation.invalidate_image_result(accepted["message"])
            return {
                "reply": accepted["message"],
                "intent": "image_rejected",
                "confidence": None,
                "followUps": [],
                "imageResult": {"status": "rejected", "reason": "invalid_classification"},
            }

        disease = accepted["classification"]
        photo_disease = self.image_knowledge_disease()
        if disease != "normal_skin":
            self.conversation.set("knowledge_disease", photo_disease)
            self.conversation.set('knowledge_origin', 'photo_screening')
        else:
            self.conversation.set("knowledge_disease", None)
            self.conversation.set('knowledge_origin', 'photo_screening')
        condition = (str(result.get('condition') or self.knowledge.data[photo_disease]['name'])
                     if disease == 'normal_skin' else self.knowledge.data[photo_disease]['name'])
        self.conversation.set("image_condition", condition)
        response = (
            f"The image model's closest match is {condition} "
            f"({accepted['confidence']:.1%} model confidence). "
            "This is a screening result, not a confirmed diagnosis."
            " The score is a model output, not your probability of having the condition."
        )
        if disease == "normal_skin":
            response += " A normal-skin match does not confirm healthy skin or rule out other conditions. Persistent or worsening symptoms need medical assessment."
        response += '\n\n' + self.knowledge.treatment_text(photo_disease)
        if self.flow.get_expected_intent(self.conversation) is not None:
            if self.flow.get_expected_intent(self.conversation) == "symptom":
                response += "\n\nIf you can, tell me what you notice, such as itching, redness, or dryness. It's okay if you're not sure."
            else:
                response += "\n\n" + self.flow.next_question(self.conversation)
        return {
            "reply": response,
            "intent": "image_classification",
            "confidence": accepted["confidence"],
            "confidenceSource": "image_model",
            "followUps": ["Treatment options for this photo", "When should I see a doctor?", "Can I send another picture?"],
            "treatmentInfo": self.knowledge.treatment_info(photo_disease),
            "classification": disease,
            "imageResult": result,
        }

    def get_uncertain_response(self, expected_intent, message=None):
        target = self.context.uncertain_target(message) if message else None
        if target:
            expected_intent = target
        if not target and self.conversation.get('pending_product_clarification'):
            return "That's okay. I cannot assess an unnamed product. You can ask about general care for a named condition, or bring the product to a pharmacist or clinician."
        if expected_intent in {"location", "duration", "severity", "medication"}:
            self.conversation.set(expected_intent, "unknown")
            field = "medication use" if expected_intent == "medication" else expected_intent
            return (
                f"That's okay. I've marked {field} as unknown. "
                + self.flow.next_question(self.conversation)
            )
        if expected_intent == "symptom":
            if self.conversation.get("image_uploaded"):
                self.conversation.set("symptoms_unknown", True)
                return (
                    "That's okay. You don't have to identify the condition yourself. "
                    "I already have your photo's screening result. "
                    + self.flow.next_question(self.conversation)
                )
            return "That's okay. Describe what you can notice, or use the image button to upload a photo."
        if expected_intent == "image_upload":
            return "You can use the image button beside the message box to select a photo, then click Send."
        if self.conversation.get('last_reply_intent') in {'image_request', 'image_followup'}:
            return "To attach a photo, click Choose photo or the image button, select a file, then click Send. You can also keep chatting in text."
        if self.conversation.get("last_knowledge_topics"):
            return "That's okay. Would you like a shorter explanation of the information we just discussed, or help understanding your photo result?"
        return "That's okay. Tell me which part feels unclear, or ask me to summarize what we know so far."

    def get_image_followup_response(self):
        condition = self.conversation.get("image_condition")
        response = "To check another photo, use the image button to attach it, then click Send."
        if condition:
            response += f" Your last classified photo's model match was {condition}."
        return response

    def get_image_explanation(self):
        if self.conversation.get("last_image_status") == "rejected":
            self.conversation.set('knowledge_disease', None)
            self.conversation.set('knowledge_origin', None)
            return "I couldn't reliably classify the latest photo. " + (self.conversation.get("last_image_feedback") or "Try another clear skin photo.")
        disease = self.image_knowledge_disease()
        self.conversation.set('knowledge_disease', disease if disease != 'normal_skin' else None)
        self.conversation.set('knowledge_origin', 'photo_screening')
        condition = self.conversation.get("image_condition") or self.conversation.get("classification").replace("_", " ").title()
        confidence = self.conversation.get("classification_confidence")
        response = (
            f"For the photo you already sent, the model's closest match is {condition} "
            f"({confidence:.1%} model confidence). "
            "This is a screening suggestion, not a confirmed diagnosis."
        )
        response += " The confidence score describes the model's prediction; it isn't a confirmed probability that you have the condition."
        overview = self.knowledge.get(disease, "overview")
        if overview:
            response += "\n\n" + overview
        response += "\n\nYou don't need to upload that photo again."
        return response

    def image_knowledge_disease(self):
        key = self.conversation.get('image_knowledge_key')
        if key in self.knowledge.data and self.conversation.get('classification'):
            return key
        disease = (self.conversation.get('classification') or '').replace(' ', '_')
        if disease == 'dermatitis':
            subtype = self.knowledge.detect_disease(self.conversation.get('image_condition') or '')
            if subtype in {'atopic_dermatitis', 'contact_dermatitis'}:
                return subtype
        return disease or None

    def remember_reply(self, result, question=None):
        if result['intent'] in {'knowledge_question', 'product_information', 'diagnosis_question'}:
            info = getattr(self, '_reply_treatment_info', None)
            if info:
                disease = info['condition_key']
                result['treatmentInfo'] = info
                if getattr(self, '_reply_from_photo', False) and disease == self.image_knowledge_disease() and self.conversation.get('classification_image_id'):
                    result['sourceImageId'] = self.conversation.get('classification_image_id')
        if result["intent"] == "image_explanation" and self.conversation.get("classification_image_id"):
            result["sourceImageId"] = self.conversation.get("classification_image_id")
        self.conversation.set("last_reply_intent", result["intent"])
        self.conversation.set("pending_question", question)
        if result['intent'] == 'image_explanation':
            self.conversation.set('last_knowledge_topics', [])
        return result

    def conversation_summary(self):
        data = self.conversation.data
        lines = ["Here's what you've told me so far:"]
        if data['symptoms']:
            lines.extend(f"Skin concern (your words): {text}" for text in data['symptoms'])
        else:
            lines.append('Skin symptoms: unknown' if data.get('symptoms_unknown') else 'Skin symptoms: not provided')
        lines.extend("Symptoms you've denied (your words): " + text for text in data.get('denied_symptoms', []))
        lines.extend("Changes you've reported (your words): " + text for text in data.get('symptom_updates', []))
        for field, label in [('location', 'Affected area'), ('duration', 'How long'), ('medication', 'Medication used')]:
            value = data.get(field)
            lines.append(f"{label}: {value if value is not None else 'not provided'}")
        if data.get('mentioned_product'):
            lines.append('Product mentioned (this alone does not mean it was used): ' + data['mentioned_product'])
        if data.get('severity') is not None:
            lines.append(f"Severity (your description): {data['severity']}")
        if data.get('classification'):
            lines.append(f"Last classified photo: {data.get('image_condition') or data['classification']} ({data['classification_confidence']:.1%} model confidence). This is a screening result, not a confirmed diagnosis.")
        if data.get('last_image_status') == 'rejected':
            lines.append('The latest uploaded photo could not be classified reliably.')
        return '\n'.join(lines)

    def simple_explanation(self, expected_intent):
        if self.conversation.get('last_reply_intent') == 'diagnosis_question':
            return self.get_diagnosis_response('is this my skin condition?')
        disease = self.conversation.get('knowledge_disease')
        topics = self.conversation.get('last_knowledge_topics')
        if expected_intent is None and disease and topics:
            return 'Short version:\n' + '\n\n'.join(
                concise(self.knowledge.get(disease, topic)) for topic in topics if self.knowledge.get(disease, topic)
            )
        if self.conversation.get('last_reply_intent') in {'image_classification', 'image_explanation', 'image_rejected', 'image_error'}:
            if self.conversation.get('last_image_status') == 'rejected':
                return self.get_image_explanation()
            return (
                f"The photo model thinks your skin looks most like {self.conversation.get('image_condition') or self.conversation.get('classification')}. "
                "It is a screening suggestion, not a confirmed diagnosis. A model confidence score does not prove you have that condition."
            )
        if expected_intent is not None:
            return self.get_clarification_response(expected_intent)
        if self.conversation.get('classification') or self.conversation.get('last_image_status') == 'rejected':
            return self.get_image_explanation()
        return "Tell me what you notice on your skin, or attach a photo. You can ask questions and skip screening questions if you prefer."

    def safety_reply(self, intent, message=None):
        return safety_response(intent, self.conversation, message)

    def suggested_questions(self):
        if self.conversation.get('knowledge_disease'):
            return ['Explain simply', 'What can I do next?', 'When should I see a doctor?']
        if self.conversation.get('classification'):
            return ['What does this result mean?', 'Summarize our conversation', 'Continue screening']
        return ['Continue screening', 'Summarize our conversation']

    def reply(self, message, image=None):
        self._reply_screening_question = None
        self._reply_management_style = None
        self._reply_from_photo = False

        # ==========================================================
        # IMAGE UPLOAD
        # ==========================================================

        if image is not None:
            self.conversation.invalidate_image_result("The latest photo has not been classified yet.")
            text_result = self.reply(message) if message.strip() else None
            if text_result and text_result["intent"] in {"emergency", "medical_attention"}:
                self.conversation.invalidate_image_result("The latest photo was not classified because the symptoms need medical attention.")
                return text_result
            result = self.get_image_response(image)
            if text_result and text_result["intent"] == "knowledge_question" and result["intent"] == "image_classification":
                # Answer captions about care using the newly classified photo.
                result["reply"] += "\n\n" + self.get_knowledge_response(message, None)
                return self.remember_reply(result)
            question = self.flow.get_expected_intent(self.conversation) if result['intent'] == 'image_classification' else None
            return self.remember_reply(result, question)

        # ==========================================================
        # 1. SEMANTIC INTENT PREDICTION
        # ==========================================================

        safety = safety_intent(message)
        if safety:
            return self.safety_reply(safety, message)
        predicted_intent, confidence = self.classifier.predict(normalize_message(message))

        # ==========================================================
        # 2. GET EXPECTED CONVERSATION INTENT
        # ==========================================================

        expected_intent = self.flow.get_expected_intent(
            self.conversation
        )
        if self.conversation.get('last_reply_intent') is not None:
            expected_intent = self.conversation.get('pending_question')

        # ==========================================================
        # 3. RESOLVE INTENT USING CONTEXT
        # ==========================================================

        final_intent = self.context.resolve(
            predicted_intent,
            message,
            self.conversation,
            expected_intent
        )

        if final_intent in SAFETY_RESPONSES:
            return self.safety_reply(final_intent, message)

        answer_message = screening_choice_answer(message, self.conversation.get('pending_screening_choices')) or message
        usage_report = self.conversation.get('pending_medication_report')
        if final_intent == 'medication' and usage_report and bare_product_answer(message):
            answer_message = usage_report + '; product: ' + message.strip()
            self.conversation.set('mentioned_product', message.strip())

        # Even a confident classifier guess must have evidence for that field.
        if final_intent in {'symptom', 'location', 'duration', 'severity', 'medication'} and not has_screening_evidence(final_intent, answer_message):
            final_intent = "clarification"

        if final_intent in {"symptom", "location", "duration", "severity", "medication"} and not any(word[0].isalpha() for word in message_words(message)):
            final_intent = "clarification"


        # ==========================================================
        # 4. HANDLE FINAL INTENT
        # ==========================================================

        if final_intent == "reset":

            self.conversation.reset()

            response = (
                "The screening has been restarted. "
                "Can you describe your skin problem?"
            )

        elif final_intent == 'new_concern':
            text_only = self.conversation.get('image_declined')
            self.conversation.reset()
            self.conversation.set('image_declined', text_only)
            if is_medication_report(message):
                self.update_conversation('medication', message)
            else:
                for field in ['location', 'duration', 'symptom']:
                    if has_screening_evidence(field, message):
                        self.update_conversation(field, message)
                        break
            response = "Let's start a new screening for this skin concern. " + self.flow.next_question(self.conversation)

        elif final_intent == 'symptom_denial':
            denials = self.conversation.get('denied_symptoms')
            if message not in denials:
                self.conversation.set('denied_symptoms', [*denials, message])
            response = "I've noted the symptoms you say are absent. "
            if self.conversation.get('image_uploaded'):
                response += "You can ask about your photo result or tell me what changes you've noticed."
            else:
                response += "What changes, if any, have you noticed on your skin? You can also say 'I'm not sure.'"

        elif final_intent == 'conversation_summary':
            response = self.conversation_summary()

        elif final_intent == 'symptom_update':
            updates = self.conversation.get('symptom_updates')
            if message not in updates:
                self.conversation.set('symptom_updates', [*updates, message])
            response = "Thanks. I've noted this change in your symptoms: " + message + '\n\n' + self.flow.next_question(self.conversation)

        elif final_intent == 'diagnosis_question':
            response = self.get_diagnosis_response(message)
            if topic_requests(message):
                response += '\n\n' + self.get_knowledge_response(message, None)

        elif final_intent == 'condition_clarification':
            choices = self.knowledge.detect_diseases(message) or self.conversation.get('pending_knowledge_choices')
            self.conversation.set('pending_knowledge_choices', choices)
            self.conversation.set('pending_knowledge_topics', topic_requests(message) or self.conversation.get('pending_knowledge_topics') or ['overview'])
            response = "You mentioned more than one condition. Which one would you like me to explain? "
            response += "A chat cannot determine which condition you have."

        elif final_intent == 'condition_comparison':
            choices = self.knowledge.detect_diseases(message)
            self.conversation.set('pending_knowledge_choices', choices)
            self.conversation.set('pending_knowledge_topics', ['overview'])
            response = 'Here is a general comparison:\n\n' + '\n\n'.join(
                self.knowledge.data[key]['name'] + ': ' + self.knowledge.get(key, 'overview') for key in choices
            ) + '\n\nThese descriptions cannot determine which condition you have.'

        elif final_intent == 'product_clarification':
            self.conversation.set('pending_product_clarification', True)
            named = self.knowledge.detect_disease(message)
            if named:
                self.conversation.set('knowledge_disease', named)
            response = "Which cream, medicine, or treatment do you mean? Tell me its name, or say 'I'm not sure.' "
            response += "I cannot choose a medicine or dose from a chat or photo."

        elif final_intent == 'product_information':
            self.conversation.set('pending_product_clarification', False)
            self._reply_treatment_info = None
            names = message_words(message) & SPECIFIC_MEDICINES
            if looks_like_question(message):
                if names:
                    self.conversation.set('mentioned_product', ', '.join(sorted(names)))
                response = "I cannot confirm whether that medicine is suitable for you or where to apply it from a chat or photo. A clinician or pharmacist can check the product, body area, and your medical history. "
                if self.conversation.get('mentioned_product'):
                    response = 'About ' + self.conversation.get('mentioned_product') + ': ' + response
            else:
                self.conversation.set('mentioned_product', message.strip())
                response = "Thanks for sharing the product name. A clinician or pharmacist needs to check its suitability for you. "
            disease = self.conversation.get('knowledge_disease')
            if disease:
                response += self.get_knowledge_response('How is ' + self.knowledge.data[disease]['name'] + ' treated?', None)
            else:
                response += "Which skin condition would you like general treatment information about?"

        elif final_intent == 'medication_clarification':
            self.conversation.set('pending_medication_report', message)
            response = "What product or medicine did you use? Tell me its name, or say 'I'm not sure.' I'll keep the treatment timeframe separate from how long you've had the skin problem."

        elif final_intent == 'duration_clarification':
            parsed_choices = clarification_request(message, self.knowledge)
            if parsed_choices and parsed_choices[0] == final_intent:
                self.conversation.set('pending_screening_choices', {'field': 'duration', 'options': parsed_choices[1]})
            response = "Which timeframe do you mean? Please give one duration, such as two days or two weeks, or say 'I'm not sure.'"

        elif final_intent == 'location_clarification':
            parsed_choices = clarification_request(message, self.knowledge)
            if parsed_choices and parsed_choices[0] == final_intent:
                self.conversation.set('pending_screening_choices', {'field': 'location', 'options': parsed_choices[1]})
            response = "Do you mean one of those areas, or are both affected? Please name the affected area or areas, or say 'I'm not sure.'"

        elif final_intent == 'question_clarification':
            response = "What do you mean: the photo result, a treatment, or a symptom you've noticed? Tell me which part you'd like help understanding."

        elif final_intent == 'simple_explanation':
            response = self.simple_explanation(expected_intent)

        elif final_intent == 'screening_pause':
            self.conversation.set('screening_paused', True)
            response = "Sure. We can skip the screening questions. Ask about your skin concern or a photo result whenever you're ready."

        elif final_intent == 'screening_resume':
            self.conversation.set('screening_paused', False)
            response = self.flow.next_question(self.conversation)

        elif final_intent == 'out_of_scope':
            response = "I can help with skin concerns, condition information, and organizing your screening details. That request is outside what this chatbot can help with. You can ask what I can do or continue discussing your skin concern."

        elif final_intent == 'emotional_support':
            response = "It's understandable to feel worried about a skin concern. We can take this one step at a time. "
            response += self.flow.next_question(self.conversation) if expected_intent is not None else "Tell me what you'd like help understanding, or ask for a summary of what you've shared."

        elif final_intent == 'bot_identity':
            response = self.get_identity_response(message)

        elif final_intent == "clarification":

            response = self.get_clarification_response(
                expected_intent
            )

        elif final_intent == "image_request":
            self.conversation.set('image_declined', False)
            # Keep location/duration supplied alongside the request.
            self.update_conversation("image_request", message)
            response = (
                "Yes. Click Choose photo below, pick a JPG, PNG, or WebP photo, "
                "then click Send. You can also use the image button beside the message box."
            )

        elif final_intent == "image_declined":
            self.conversation.set('image_declined', True)
            response = "That's okay. We can continue in text. "
            if expected_intent not in {None, "image_upload"}:
                response += self.flow.next_question(self.conversation)
            else:
                response += "Tell me what you'd like to discuss about your skin concern."

        elif final_intent == "uncertain_answer":
            response = self.get_uncertain_response(expected_intent, message)

        elif final_intent == "image_followup":
            response = self.get_image_followup_response()

        elif final_intent == "image_explanation":
            response = self.get_image_explanation()

        elif final_intent == "knowledge_question":

            if is_self_report(message) and symptom_mentions(message)[0] and not is_course_question(message):
                self.update_conversation('symptom', message)

            response = self.get_knowledge_response(
                message,
                expected_intent
            )

        elif final_intent == "correction":

            response = self.handle_correction(
                message
            )

        elif final_intent == "invalid_location":

            response = (
                "Which part of your body is affected? "
                "You can say something like 'my arm' or 'my forehead,' "
                "or answer 'I'm not sure.'"
            )

        elif final_intent == "invalid_duration":
            if message.strip().replace('.', '', 1).isdigit():
                response = f"Do you mean {message.strip()} days, weeks, or months? Please include the time unit so I can record it correctly."
            else:
                response = (
                "About how long have you noticed the skin problem? "
                "You can say 'two days,' '2 weeks,' or 'I'm not sure.'"
                )

        elif final_intent == "invalid_severity":

            response = (
                "I didn't understand the severity. "
                "Please answer with mild, moderate, or severe."
            )

        elif final_intent == "invalid_medication":

            response = (
                "Have you used a cream, medicine, or another treatment for it? "
                "Tell me what you used, or say 'none' or 'I'm not sure.'"
            )

        elif final_intent == 'greeting' and self.conversation.get('image_uploaded'):
            response = "Hi again! What would you like to discuss about your skin concern? You can ask about your photo result, too."

        elif final_intent in {'greeting', 'thanks'}:
            response = 'Hi! ' if final_intent == 'greeting' else "You're welcome. "
            response += self.flow.next_question(self.conversation) if expected_intent is not None else "What would you like to discuss about your skin concern? You can also ask to continue screening."

        elif final_intent == 'confirmation':
            kind = confirmation_kind(message)
            if kind == 'negative':
                response = "Thanks for correcting me. Tell me which detail is wrong—the affected area, how long you've had it, or the medication—or give the corrected detail."
            elif kind == 'uncertain':
                response = "That's okay. You can tell me which detail is unclear, or say 'I'm not sure' to skip the screening question."
            elif expected_intent == 'medication':
                response = "What did you use? You can name the cream or medicine, or say 'I'm not sure.'"
            else:
                response = "Thanks for confirming. " + (self.flow.next_question(self.conversation) if expected_intent is not None else "You can ask another question or continue screening whenever you're ready.")

        else:

            if final_intent in {'symptom', 'location', 'duration', 'severity', 'medication'}:
                self.update_conversation(final_intent, answer_message)

            screening_intents = {
                "symptom",
                "location",
                "duration",
                "severity",
                "medication",
            }

            if final_intent in screening_intents:

                response = self.get_screening_response(
                    final_intent
                )

            elif final_intent == "awaiting_image":

                response = (
                    "The screening information is complete. "
                    "Please upload a clear picture of the affected skin "
                    "to continue."
                )

            else:

                response = self.get_response(
                    final_intent
                )

        # ==========================================================
        # RETURN RESULT
        # ==========================================================

        reply_confidence, confidence_source = None, None
        if final_intent == "image_explanation" and self.conversation.get('last_image_status') != 'rejected':
            reply_confidence = self.conversation.get("classification_confidence")
            confidence_source = "image_model"
        elif final_intent == predicted_intent:
            reply_confidence, confidence_source = float(confidence), "intent_model"
        asks_field = {'symptom', 'symptom_update', 'location', 'duration', 'severity', 'medication', 'reset', 'correction', 'screening_resume', 'new_concern'}
        pending = self.flow.get_expected_intent(self.conversation) if final_intent in asks_field else None
        if final_intent.startswith('invalid_') or final_intent == 'clarification':
            pending = expected_intent
            attempts = self.conversation.get('invalid_answers') + 1
            self.conversation.set('invalid_answers', attempts)
            if attempts >= 2 and pending is not None:
                response = self.get_clarification_response(pending) + " You can also say 'skip' or 'I'm not sure.'"
        else:
            self.conversation.set('invalid_answers', 0)
        if final_intent == 'uncertain_answer' and expected_intent is not None:
            pending = self.flow.get_expected_intent(self.conversation)
        if final_intent == 'simple_explanation':
            pending = expected_intent if self.conversation.get('last_reply_intent') not in {'image_classification', 'image_explanation', 'image_rejected'} else None
        if final_intent in {'greeting', 'thanks', 'emotional_support'}:
            pending = None if final_intent == 'greeting' and self.conversation.get('image_uploaded') else expected_intent
        if final_intent == 'image_declined' and expected_intent not in {None, 'image_upload'}:
            pending = self.flow.get_expected_intent(self.conversation)
        if final_intent == 'confirmation' and confirmation_kind(message) == 'affirmative':
            pending = expected_intent
        if final_intent == 'knowledge_question' and is_care_question(message):
            pending = expected_intent
        if final_intent == 'knowledge_question' and self._reply_screening_question is not None:
            pending = self._reply_screening_question
        if final_intent == 'symptom_denial':
            pending = None if self.conversation.get('image_uploaded') else 'symptom'
        if final_intent in {'duration_clarification', 'location_clarification'}:
            pending = final_intent.removesuffix('_clarification')
        if final_intent == 'medication_clarification':
            pending = 'medication'
        followups = self.flow.follow_ups(self.conversation, pending) if pending is not None else []
        if pending is None and final_intent in {'knowledge_question', 'diagnosis_question', 'simple_explanation', 'conversation_summary', 'uncertain_answer', 'screening_pause'}:
            followups = self.suggested_questions()
        if final_intent == 'diagnosis_question' and self.conversation.get('knowledge_disease'):
            followups = ['Is it treatable?', 'When should I see a doctor?', 'Summarize our conversation']
        if final_intent == 'knowledge_question' and self._reply_management_style in {'treatability', 'curability'}:
            condition = self.knowledge.data[self.conversation.get('knowledge_disease')]['name']
            followups = ['What can I do next?', 'Treatment options for ' + condition, 'When should I see a doctor?']
        if final_intent in {'bot_identity', 'out_of_scope'}:
            followups = ['Continue screening', 'Summarize our conversation']
        if final_intent == 'knowledge_question' and not is_care_question(message) and self.conversation.get('knowledge_disease') is None and self.conversation.get('last_image_status') != 'rejected' and self.conversation.get('classification') != 'normal_skin':
            followups = self.knowledge.choices()
        if final_intent == 'invalid_duration' and message.strip().replace('.', '', 1).isdigit():
            followups = [f'{message.strip()} days', f'{message.strip()} weeks', f'{message.strip()} months']
        if final_intent == 'condition_clarification':
            followups = [self.knowledge.data[key]['name'] for key in self.conversation.get('pending_knowledge_choices')]
        if final_intent == 'product_information' and not self.conversation.get('knowledge_disease'):
            followups = self.knowledge.choices()
        choices = self.conversation.get('pending_screening_choices')
        if final_intent in {'location_clarification', 'duration_clarification'} and choices:
            followups = list(choices['options']) + (['Both areas'] if choices['field'] == 'location' else []) + ["I'm not sure"]
        if final_intent not in {'location_clarification', 'duration_clarification', 'thanks', 'greeting', 'confirmation', 'simple_explanation'}:
            self.conversation.set('pending_screening_choices', None)
        if final_intent not in {'medication_clarification', 'thanks', 'greeting', 'confirmation', 'simple_explanation'}:
            self.conversation.set('pending_medication_report', None)
        if final_intent not in {'product_clarification', 'greeting', 'thanks', 'confirmation', 'uncertain_answer'}:
            self.conversation.set('pending_product_clarification', False)
        return self.remember_reply({
            "reply": response,
            "intent": str(final_intent),
            "confidence": reply_confidence,
            "confidenceSource": confidence_source,
            "predictedIntent": str(predicted_intent),
            "modelConfidence": float(confidence),
            "action": "upload_image" if pending == 'image_upload' or final_intent in {"image_request", "image_followup", "awaiting_image"} or (final_intent == 'image_explanation' and self.conversation.get('last_image_status') == 'rejected') else None,
            "followUps": followups,
        }, pending)

    # ==============================================================
    # UPDATE CONVERSATION MEMORY
    # ==============================================================

    def update_conversation(self, intent, message):

        if intent == 'medication':
            skin_parts, medication_part = medication_report_parts(message, self.conversation.get('mentioned_product'))
            for part in skin_parts:
                for field in ['location', 'duration', 'symptom']:
                    if has_screening_evidence(field, part):
                        self.update_conversation(field, part)
                        break
            message = medication_part

        text = normalize_message(message)
        words = message_words(text)

        # A screening answer can contain symptoms as well as its primary field.
        if intent in {"location", "duration", "severity", "medication", "image_request"} and symptom_mentions(message)[0]:
            self.conversation.add_symptom(message)

        # ==========================================================
        # PRIMARY INTENT
        # ==========================================================

        if intent == "symptom":
            self.conversation.add_symptom(message)

        elif intent == "location":
            self.conversation.set(
                "location",
                message
            )

        elif intent == "duration":
            self.conversation.set(
                "duration",
                message
            )

        elif intent == "severity":
            self.conversation.set(
                "severity",
                message
            )

        if intent == "medication":
            if no_medication(text):
                self.conversation.set(
                    "medication",
                    "none"
                )

            else:
                self.conversation.set(
                    "medication",
                    message
                )

        #elif intent == "image_upload":
        #    self.conversation.set(
        #        "image_uploaded",
        #        True
        #    )

        # ==========================================================
        # ADDITIONAL INFORMATION IN THE SAME MESSAGE
        # ==========================================================

        location_words = LOCATION_WORDS

        severity_words = SEVERITY_WORDS

        has_location = any(
            word in words
            for word in location_words
        )

        has_duration = has_duration_answer(message)

        has_severity = any(
            word in words
            for word in severity_words
        )

        # ==========================================================
        # STORE ADDITIONAL INFORMATION
        # ==========================================================

        # Don't overwrite a value with the entire message
        # when it was already saved as the primary intent.

        if has_location and intent not in {"location", "medication"}:
            self.conversation.set(
                "location",
                message
            )

        if has_duration and intent not in {"duration", "medication"}:
            self.conversation.set(
                "duration",
                message
            )

        if has_severity and intent not in {"severity", "medication"}:
            self.conversation.set(
                "severity",
                message
            )

    # ==============================================================
    # CLARIFICATION RESPONSES
    # ==============================================================

    def get_clarification_response(self, expected_intent):

        clarifications = {

            "symptom": (
                "Could you describe what you're noticing on your skin? "
                "For example, itching, redness, dryness, a rash, "
                "scaling, or another skin concern."
            ),

            "location": (
                "I mean, where on your body is the affected skin located? "
                "For example, your face, arm, leg, back, neck, or scalp."
            ),

            "duration": (
                "I mean, how long have you had this skin problem? "
                "For example, a few days, two weeks, or several months."
            ),

            "severity": (
                "I mean, how much is the skin problem bothering you? "
                "You can describe it as mild, moderate, or severe."
            ),

            "medication": (
                "I mean, have you applied or taken anything for the "
                "skin problem? For example, a cream, ointment, lotion, "
                "or medicine. You can also say none."
            ),

            "image_upload": (
                "I mean, please upload a clear photo of the affected "
                "skin so I can continue the screening."
            ),
        }

        return clarifications.get(
            expected_intent,
            (
                "Sure. Could you tell me which part "
                "you'd like me to explain?"
            )
        )

    # ==============================================================
    # NORMAL INTENT RESPONSE
    # ==============================================================

    def get_response(self, intent):

        for item in self.data["intents"]:

            if item["tag"] == intent:

                return random.choice(
                    item["responses"]
                )

        return "Sorry, I don't understand."

    def get_identity_response(self, message):
        text = normalize_message(message)
        if any(word in text for word in ['score', 'confidence', 'percentage', 'accuracy', 'accurate']):
            return "A text-intent score describes how the model matched your message to a category. A photo model score describes its image match. Neither is your probability of having a disease. Text-intent benchmark accuracy measures correct message categories on that test set; it does not measure diagnostic accuracy. This prototype has not established clinical accuracy or score calibration."
        if 'learn' in text or 'train' in text:
            return "I use a trained text model to recognize what you're asking. My model is updated through a separate training process; saving a conversation does not automatically train me on it."
        if any(word in text for word in ['private', 'privacy', 'save', 'store', 'data', 'what happens', 'secure', 'encrypted', 'who can']):
            return "Your chats and uploaded photos are saved on the Flamma server and linked to this browser session. They are not encrypted by this app. People using the same browser profile or with access to the server files may access them; this prototype has no account sign-in. Clear history removes your saved application records for this browser, including photos. Exported files, backups, and logs from older versions are separate copies."
        if 'come from' in text or 'source' in text:
            return "My condition explanations come from Flamma's local skin-information library. Some entries include American Academy of Dermatology sources. I can explain a named condition, but I cannot confirm a diagnosis from a chat."
        if any(word in text for word in ['doctor', 'dermatologist', 'diagnos', 'reliable', 'accurate', 'trust', 'limits']):
            return "I can organize your symptoms and explain general skin information. I cannot confirm a diagnosis, choose a prescription or dose, or replace a clinician's assessment. Photo results are screening suggestions."
        if 'work' in text or 'technology' in text:
            return "I use a trained text-intent model, conversation rules, and a local skin-information library. I keep track of details in this chat so you can ask follow-up questions, correct information, or request a summary."
        return "I'm Flamma. I can help you describe a skin concern, explain named conditions, discuss general care from my information library, remember details in this conversation, and summarize what you've shared. You can pause or resume screening at any time."


    def get_knowledge_response(self, message, expected_intent):
        self._reply_treatment_info = None
        self._reply_screening_question = None
        self._reply_management_style = None
        parsed = self.knowledge.parse_question(message)
        self._reply_from_photo = False
        photo_reference = bool(message_words(message) & PHOTO_REFERENCES)

        disease = parsed["disease"]
        topics = parsed["topics"]
        condition_followup = self.knowledge.is_condition_followup(message)
        inherited_style = None
        if condition_followup:
            if not topic_requests(message):
                topics = self.conversation.get('last_knowledge_topics') or topics
                inherited_style = self.conversation.get('last_management_style')
        choices = self.conversation.get('pending_knowledge_choices')
        ordinal = knowledge_choice_index(message)
        selected = None
        if choices and ordinal is not None and ordinal < len(choices):
            selected = choices[ordinal]
        elif disease in choices and (self.context.normalize(message) in self.knowledge.aliases or condition_followup):
            selected = disease
        if selected:
            disease = selected
            topics = self.conversation.get('pending_knowledge_topics') or ['overview']
            inherited_style = None
        named_condition = disease is not None
        if disease:
            self.conversation.set('pending_knowledge_choices', [])
            self.conversation.set('pending_knowledge_topics', [])
        from_photo = False

        if is_care_question(message):
            # General referral advice does not require a diagnosis or photo.
            mentioned = self.knowledge.detect_diseases(message)
            if len(mentioned) > 1:
                self.conversation.set('pending_knowledge_choices', mentioned)
                self.conversation.set('pending_knowledge_topics', ['overview'])
                self.conversation.set('last_knowledge_topics', ['referral'])
                return GENERAL_CARE_GUIDANCE
            disease = disease or (self.image_knowledge_disease() if photo_reference else self.conversation.get('knowledge_disease'))
            specific = self.knowledge.get(disease, 'referral') if disease else None
            self.conversation.set('last_knowledge_topics', ['referral'])
            if disease:
                self.conversation.set('knowledge_disease', disease if disease != 'normal_skin' else None)
                self.conversation.set('knowledge_origin', 'named_condition' if named_condition else 'photo_screening' if photo_reference else self.conversation.get('knowledge_origin'))
            if specific:
                return self.photo_topic_note(message, disease) + GENERAL_CARE_GUIDANCE + f"\n\nFor {self.knowledge.data[disease]['name']}: " + specific
            return GENERAL_CARE_GUIDANCE

        # ----------------------------------------------------------
        # USE PREVIOUS KNOWLEDGE CONTEXT
        # ----------------------------------------------------------

        if disease is None:
            previous_disease = self.conversation.get(
                "knowledge_disease"
            )
            if self.conversation.get('last_image_status') == 'rejected' and (previous_disease is None or photo_reference):
                return "I couldn't reliably classify the latest photo, so I can't use it to suggest condition-specific care. You can ask about the rejection, send another photo, or name a condition for general information."
            if self.conversation.get('classification') and (is_disease_overview_question(message) or photo_reference) and (previous_disease is None or photo_reference):
                disease = self.image_knowledge_disease()
                from_photo = True
            elif previous_disease is not None:
                disease = previous_disease
                from_photo = disease == self.image_knowledge_disease() and self.conversation.get('knowledge_origin') == 'photo_screening'
            elif self.conversation.get('classification') == 'normal_skin':
                if 'course' in topics:
                    self.conversation.set('last_knowledge_topics', ['course'])
                    self._reply_from_photo = self.conversation.get('knowledge_origin') == 'photo_screening'
                    self._reply_treatment_info = self.knowledge.course_info('normal_skin')
                    return self.knowledge.get('normal_skin', 'course')
                if 'management' in topics:
                    self._reply_from_photo = self.conversation.get('knowledge_origin') == 'photo_screening'
                    self.conversation.set('last_knowledge_topics', topics)
                    self._reply_treatment_info = self.knowledge.treatment_info('normal_skin')
                    return self.knowledge.get('normal_skin', 'overview') + '\n\n' + self.knowledge.treatment_text('normal_skin')
                return "The photo's screening result did not match a supported skin condition. It doesn't establish a diagnosis or a treatment plan. I can explain the image result or help you organize the symptoms you've noticed."

        # ----------------------------------------------------------
        # DISEASE STILL UNKNOWN
        # ----------------------------------------------------------

        if disease is None:
            return (
                "I don't have a disease name or an accepted photo result to explain yet. "
                "You can upload a photo or choose a condition for general information. "
                "Which of these conditions would you like to know about? "
                + ', '.join(self.knowledge.choices()) + '.'
            )

        self._reply_from_photo = from_photo
        self.conversation.set('knowledge_origin', 'photo_screening' if from_photo else 'named_condition')
        if disease == 'normal_skin':
            self.conversation.set('knowledge_disease', None)
            if 'course' in topics:
                self.conversation.set('last_knowledge_topics', ['course'])
                self._reply_treatment_info = self.knowledge.course_info('normal_skin')
                return self.knowledge.get('normal_skin', 'course')
            if 'management' in topic_requests(message):
                self.conversation.set('last_knowledge_topics', ['management'])
                self._reply_treatment_info = self.knowledge.treatment_info('normal_skin')
                return self.knowledge.get('normal_skin', 'overview') + '\n\n' + self.knowledge.treatment_text('normal_skin')
            self.conversation.set('last_knowledge_topics', ['overview'])
            return self.knowledge.get('normal_skin', 'overview')

        if is_disease_overview_question(message) and topics == ['overview']:
            topics = ['overview', 'symptoms', 'management']

        # ----------------------------------------------------------
        # REMEMBER CURRENT KNOWLEDGE DISEASE
        # ----------------------------------------------------------

        self.conversation.set(
            "knowledge_disease",
            disease
        )

        # ----------------------------------------------------------
        # RETRIEVE KNOWLEDGE
        # ----------------------------------------------------------

        self.conversation.set('last_knowledge_topics', topics)
        style = management_style(message) or inherited_style
        self.conversation.set('last_management_style', style if topics == ['management'] else None)
        if topics == ['management'] and style:
            return self.photo_topic_note(message, disease) + self.get_brief_management_response(disease, style, from_photo)
        labels = {'course': 'Usual course', 'symptoms': 'Symptoms', 'causes': 'Causes', 'contagious': 'Spreading to others', 'management': 'Management summary', 'referral': 'Getting professional help', 'overview': 'Overview'}
        include_treatment_details = 'management' in topic_requests(message) or (selected and 'management' in topics)
        answers = []
        for topic in topics:
            knowledge = self.knowledge.get(disease, topic)
            if knowledge:
                if dialogue_act(message) == 'simple_explanation':
                    knowledge = concise(knowledge)
                answers.append(f'{labels[topic]}: {knowledge}' if len(topics) > 1 else knowledge)
                if topic == 'course':
                    self._reply_treatment_info = self.knowledge.course_info(disease)
                if topic == 'management':
                    if include_treatment_details:
                        answers.append(self.knowledge.treatment_text(disease))
                    self._reply_treatment_info = self.knowledge.treatment_info(disease)
        if not answers:
            return "I don't have enough information in my knowledge base to answer that accurately. You can ask about symptoms, causes, general care, or getting the condition checked."
        if 'course' in topics and 'management' in topics:
            course_info = self.knowledge.course_info(disease)
            care_info = self.knowledge.treatment_info(disease)
            if course_info and care_info:
                sources = {}
                for info in [care_info, course_info]:
                    for source in info['sources']:
                        sources[source['url']] = dict(source, source_checked_on=info['source_checked_on'])
                self._reply_treatment_info = dict(care_info, topic='course_and_management',
                                                  sources=list(sources.values()), source_checked_on=None)
        answer = f"General information about {self.knowledge.data[disease]['name']}:\n\n" + '\n\n'.join(answers)
        if from_photo:
            answer = "I'm explaining your photo model's screening suggestion, not a confirmed diagnosis.\n\n" + answer
        if is_medication_question(message):
            answer = "I can't choose a medicine or dose from a chat or screening photo. " + answer
        site_note = self.condition_site_note(disease)
        if site_note:
            answer = site_note + '\n\nThe following is general condition information:\n\n' + answer
        return self.photo_topic_note(message, disease) + answer

    def photo_topic_note(self, message, disease):
        """Distinguish a named condition from the latest photo's actual result."""
        own_photo = re.search(r'\b(?:my|this|that|these|those|latest|uploaded) (?:\w+ )?(?:photo|photos|picture|pictures|image|images|pic|pics|result|results)\b', normalize_message(message))
        if not own_photo or self._reply_from_photo:
            return ''
        if self.conversation.get('last_image_status') == 'rejected':
            return "The latest photo could not be classified reliably. The following is general information about " + self.knowledge.data[disease]['name'] + "; it does not confirm what the photo shows.\n\n"
        photo_disease = self.image_knowledge_disease()
        if photo_disease and photo_disease != disease:
            match = self.conversation.get('image_condition') or self.knowledge.data[photo_disease]['name']
            return "Your latest photo's screening match was " + match + ". The following is general information about " + self.knowledge.data[disease]['name'] + "; it does not confirm that named condition in your photo.\n\n"
        return ''

    def condition_site_note(self, disease):
        if disease == 'rosacea' and message_words(self.conversation.get('location') or '') & {'butt', 'buttocks'}:
            info = self.knowledge.treatment_info(disease) or {}
            return info.get('nonfacial_site_note', '')
        return ''

    def get_brief_management_response(self, disease, style, from_photo):
        info = self.knowledge.treatment_info(disease)
        if info is None:
            return concise(self.knowledge.get(disease, 'management') or 'A clinician can help identify the condition and discuss care.')
        self._reply_management_style = style
        self._reply_treatment_info = info
        name = self.knowledge.data[disease]['name']
        site_note = self.condition_site_note(disease)
        if style in {'treatability', 'curability'}:
            text = info.get('brief_answers', {}).get(style) or concise(self.knowledge.get(disease, 'management'))
            self._reply_treatment_info = dict(info, source_checked_on=info.get('brief_answers_checked_on', info['source_checked_on']))
            prefix = 'About ' + name + ':\n'
        else:
            steps = [*info['self_care'][:2], info['seek_care']]
            if site_note:
                steps = ['Arrange an assessment of the skin concern you described.']
            text = '\n'.join(str(index) + '. ' + step for index, step in enumerate(steps, 1))
            prefix = 'General next steps for ' + name + ':\n'
            question = self.flow.get_expected_intent(self.conversation)
            if question in {'symptom', 'location', 'duration', 'medication'}:
                text += '\n\nTo understand your skin concern better: ' + self.flow.next_question(self.conversation)
                self._reply_screening_question = question
        if from_photo:
            prefix = "For the photo model's screening suggestion of " + name + ' (not a diagnosis):\n'
        return (site_note + '\n\n' if site_note else '') + prefix + text

    def get_diagnosis_response(self, message):
        self._reply_treatment_info = None
        named = self.knowledge.detect_disease(message)
        if named:
            self.conversation.set('knowledge_disease', named)
            self.conversation.set('knowledge_origin', 'named_condition')
        disease = named or self.conversation.get('knowledge_disease')
        answer = 'I cannot confirm your skin condition from a chat or screening photo. '
        if disease and disease != 'normal_skin':
            answer += self.knowledge.data[disease]['name'] + ' is the condition we are discussing, not a confirmed diagnosis. '
        if self.conversation.get('last_image_status') == 'rejected':
            answer += 'The latest photo was not classified reliably, so it does not establish which condition you have. '
        elif self.conversation.get('classification'):
            answer += 'The latest photo model\'s screening suggestion was ' + (self.conversation.get('image_condition') or self.conversation.get('classification')) + '; it is not a confirmed diagnosis. '
        answer += 'A doctor or dermatologist can assess your skin and confirm the cause. You can still ask for general information or tell me what symptoms you have noticed.'
        return answer

    def get_screening_response(self, completed_intent):

        acknowledgements = {
            "symptom": "Thanks for describing what you're experiencing.",
            "location": "Got it. I've noted where the affected area is.",
            "duration": "Thanks. I've noted how long you've had it.",
            "severity": "Understood. I've noted the severity.",
            "medication": "Thanks. I've noted that information."
        }

        acknowledgement = acknowledgements.get(
            completed_intent,
            ""
        )

        if completed_intent == 'medication':
            data = self.conversation.data
            details = []
            location, duration = data.get('location'), data.get('duration')
            if location and location == duration and location != 'unknown':
                details.append('Rash area and timeframe (your words): ' + location)
            else:
                if location is not None:
                    details.append('Affected area (your words): ' + location)
                if duration is not None:
                    details.append('Rash timeframe (your words): ' + duration)
            medication = data.get('medication')
            if medication == 'none':
                details.append("You said you haven't used a treatment.")
            elif medication == 'unknown':
                details.append('Treatment used: not sure.')
            elif medication:
                details.append('Treatment use (your words): ' + medication)
            if details:
                acknowledgement = "Thanks. Here's what I recorded:\n" + '\n'.join(details)

        next_question = self.flow.next_question(
            self.conversation
        )

        if acknowledgement:
            if completed_intent == 'location':
                note = self.condition_site_note(self.conversation.get('knowledge_disease'))
                if note:
                    acknowledgement += '\n' + note
            return f"{acknowledgement}\n\n{next_question}"

        return next_question

    def handle_correction(self, message):
        updates = correction_updates(message, self.conversation.get('mentioned_product'))
        if not updates:
            return (
                "Sure. What would you like to correct: the affected area, "
                "how long you've had it, or the medication you've used?"
            )
        for field, value in updates.items():
            self.conversation.set(field, value)
        labels = {'location': 'affected location', 'duration': 'duration',
                  'severity': 'severity', 'medication': 'medication information'}
        changed = ', '.join(labels[field] for field in updates)
        return f"No problem. I've updated the {changed}. " + self.flow.next_question(self.conversation)
