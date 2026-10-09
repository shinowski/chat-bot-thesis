from copy import copy
from math import isfinite
from pathlib import Path
import random
from model.knowledge_base import KnowledgeBase, is_disease_overview_question
from model.context_intent import ContextIntent
from model.conversation import Conversation
from model.flow_manager import FlowManager
from model.dataset import Dataset
from model.dialogue import concise, correction_updates, dialogue_act, is_medication_question, is_self_report
from model.image_classifier import ImageClassifier
from model.text_understanding import (
    LOCATION_WORDS, SYMPTOM_WORDS,
    has_duration_answer, has_screening_evidence, message_words, no_medication, normalize_message,
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
        self.conversation.set("last_knowledge_topics", [])

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
        self.classifier.load(project_dir / "semantic_classifier.pkl")

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
        result = self.image_classifier.predict(image)
        if result["status"] == "rejected":
            reasons = {
                "no_skin_detected": "I couldn't detect enough skin in this image. Please upload a clear, close-up photo of the affected area.",
                "out_of_scope": "This image falls outside the image model's supported conditions. I couldn't classify it reliably.",
                "low_confidence": "The image model isn't confident enough to classify this photo. Please try a clearer photo with good lighting.",
                "inconclusive": "The image model couldn't reach a reliable result from this photo. Please try a clear close-up of the affected skin in good lighting.",
            }
            feedback = reasons.get(result.get("reason"), "I couldn't read this image. Please upload a JPG, PNG, or WebP photo.")
            self.conversation.set("last_image_status", "rejected")
            self.conversation.set("last_image_feedback", feedback)
            self.conversation.set("last_knowledge_topics", [])
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
            self.conversation.set("last_image_status", "rejected")
            self.conversation.set("last_image_feedback", accepted["message"])
            self.conversation.set("last_knowledge_topics", [])
            return {
                "reply": accepted["message"],
                "intent": "image_rejected",
                "confidence": None,
                "followUps": [],
                "imageResult": {"status": "rejected", "reason": "invalid_classification"},
            }

        disease = accepted["classification"]
        if disease != "normal_skin":
            specific = str(result.get('predicted_class', '')).replace(' ', '_')
            self.conversation.set("knowledge_disease", specific if specific in self.knowledge.data else disease.replace(" ", "_"))
        else:
            self.conversation.set("knowledge_disease", None)
        condition = str(result.get("condition") or result["predicted_class"].replace("_", " ").title())
        self.conversation.set("image_condition", condition)
        response = (
            f"The image model's closest match is {condition} "
            f"({accepted['confidence']:.1%} model confidence). "
            "This is a screening result, not a confirmed diagnosis."
        )
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
            "followUps": ["What does this result mean?", "Can I send another picture?"],
            "classification": disease,
            "imageResult": result,
        }

    def get_uncertain_response(self, expected_intent):
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
            return "I couldn't reliably classify the latest photo. " + (self.conversation.get("last_image_feedback") or "Try another clear skin photo.")
        condition = self.conversation.get("image_condition") or self.conversation.get("classification").replace("_", " ").title()
        confidence = self.conversation.get("classification_confidence")
        response = (
            f"For the photo you already sent, the model's closest match is {condition} "
            f"({confidence:.1%} model confidence). "
            "This is a screening suggestion, not a confirmed diagnosis."
        )
        response += " The confidence score describes the model's prediction; it isn't a confirmed probability that you have the condition."
        disease = self.image_knowledge_disease()
        overview = self.knowledge.get(disease, "overview")
        if overview:
            response += "\n\n" + overview
        response += "\n\nYou don't need to upload that photo again."
        return response

    def image_knowledge_disease(self):
        disease = (self.conversation.get('classification') or '').replace(' ', '_')
        if disease == 'dermatitis':
            subtype = self.knowledge.detect_disease(self.conversation.get('image_condition') or '')
            if subtype in {'atopic_dermatitis', 'contact_dermatitis'}:
                return subtype
        return disease or None

    def remember_reply(self, result, question=None):
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
        for field, label in [('location', 'Affected area'), ('duration', 'How long'), ('medication', 'Medication used')]:
            value = data.get(field)
            lines.append(f"{label}: {value if value is not None else 'not provided'}")
        if data.get('severity') is not None:
            lines.append(f"Severity (your description): {data['severity']}")
        if data.get('classification'):
            lines.append(f"Last classified photo: {data.get('image_condition') or data['classification']} ({data['classification_confidence']:.1%} model confidence). This is a screening result, not a confirmed diagnosis.")
        if data.get('last_image_status') == 'rejected':
            lines.append('The latest uploaded photo could not be classified reliably.')
        return '\n'.join(lines)

    def simple_explanation(self, expected_intent):
        disease = self.conversation.get('knowledge_disease')
        topics = self.conversation.get('last_knowledge_topics')
        if expected_intent is None and disease and topics:
            return 'Short version:\n' + '\n\n'.join(
                concise(self.knowledge.get(disease, topic)) for topic in topics if self.knowledge.get(disease, topic)
            )
        if self.conversation.get('last_reply_intent') in {'image_classification', 'image_explanation', 'image_rejected'}:
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

    def suggested_questions(self):
        if self.conversation.get('knowledge_disease'):
            return ['Explain simply', 'What can I do next?', 'When should I see a doctor?']
        if self.conversation.get('classification'):
            return ['What does this result mean?', 'Summarize our conversation', 'Continue screening']
        return ['Continue screening', 'Summarize our conversation']

    def reply(self, message, image=None):

        # ==========================================================
        # IMAGE UPLOAD
        # ==========================================================

        if image is not None:
            text_result = self.reply(message) if message.strip() else None
            if text_result and text_result["intent"] == "emergency":
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

        # Even a confident classifier guess must have evidence for that field.
        if final_intent in {'symptom', 'location', 'duration', 'severity', 'medication'} and not has_screening_evidence(final_intent, message):
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

        elif final_intent == 'conversation_summary':
            response = self.conversation_summary()

        elif final_intent == 'simple_explanation':
            response = self.simple_explanation(expected_intent)

        elif final_intent == 'screening_pause':
            self.conversation.set('screening_paused', True)
            response = "Sure. We can skip the screening questions. Ask about your skin concern or a photo result whenever you're ready."

        elif final_intent == 'screening_resume':
            self.conversation.set('screening_paused', False)
            response = self.flow.next_question(self.conversation)

        elif final_intent == "clarification":

            response = self.get_clarification_response(
                expected_intent
            )

        elif final_intent == "image_request":
            # Keep location/duration supplied alongside the request.
            self.update_conversation("image_request", message)
            response = (
                "Yes. Click Choose photo below, pick a JPG, PNG, or WebP photo, "
                "then click Send. You can also use the image button beside the message box."
            )

        elif final_intent == "image_declined":
            response = "That's okay. We can continue in text. "
            if expected_intent not in {None, "image_upload"}:
                response += self.flow.next_question(self.conversation)
            else:
                response += "Tell me what you'd like to discuss about your skin concern."

        elif final_intent == "uncertain_answer":
            response = self.get_uncertain_response(expected_intent)

        elif final_intent == "image_followup":
            response = self.get_image_followup_response()

        elif final_intent == "image_explanation":
            response = self.get_image_explanation()

        elif final_intent == "knowledge_question":

            if is_self_report(message) and message_words(message) & SYMPTOM_WORDS:
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

        elif final_intent == "greeting" and (self.conversation.get("image_uploaded") or self.conversation.get('screening_paused')):
            response = "Hi again! What would you like to discuss about your skin concern?"
            if self.conversation.get('image_uploaded'):
                response += " You can ask about your photo result, too."

        elif final_intent == 'confirmation' and expected_intent == 'medication':
            response = "What did you use? You can name the cream or medicine, or say 'I'm not sure.'"

        else:

            if final_intent in {'symptom', 'location', 'duration', 'severity', 'medication'}:
                self.update_conversation(final_intent, message)

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
        # DEBUG INFORMATION
        # ==========================================================

        print("\n========== SEMANTIC CHATBOT ==========")
        print("User:", message)
        print("MiniLM prediction:", predicted_intent)
        print("MiniLM confidence:", round(float(confidence), 4))
        print("Expected intent:", expected_intent)
        print("Final intent:", final_intent)
        print("Conversation:", self.conversation.show())
        print("======================================\n")

        # ==========================================================
        # RETURN RESULT
        # ==========================================================

        reply_confidence, confidence_source = None, None
        if final_intent == "image_explanation" and self.conversation.get('last_image_status') != 'rejected':
            reply_confidence = self.conversation.get("classification_confidence")
            confidence_source = "image_model"
        elif final_intent == predicted_intent:
            reply_confidence, confidence_source = float(confidence), "intent_model"
        asks_field = {'symptom', 'location', 'duration', 'severity', 'medication', 'reset', 'correction', 'screening_resume'}
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
        if final_intent == 'greeting' and not self.conversation.get('image_uploaded'):
            pending = 'symptom' if not self.conversation.get('screening_paused') else None
        if final_intent == 'image_declined' and expected_intent not in {None, 'image_upload'}:
            pending = self.flow.get_expected_intent(self.conversation)
        if final_intent == 'confirmation' and expected_intent == 'medication':
            pending = 'medication'
        followups = self.flow.follow_ups(self.conversation, pending) if pending is not None else []
        if pending is None and final_intent in {'knowledge_question', 'simple_explanation', 'conversation_summary', 'uncertain_answer', 'screening_pause'}:
            followups = self.suggested_questions()
        if final_intent == 'knowledge_question' and self.conversation.get('knowledge_disease') is None and self.conversation.get('last_image_status') != 'rejected' and self.conversation.get('classification') != 'normal_skin':
            followups = self.knowledge.choices()
        if final_intent == 'invalid_duration' and message.strip().replace('.', '', 1).isdigit():
            followups = [f'{message.strip()} days', f'{message.strip()} weeks', f'{message.strip()} months']
        return self.remember_reply({
            "reply": response,
            "intent": str(final_intent),
            "confidence": reply_confidence,
            "confidenceSource": confidence_source,
            "predictedIntent": str(predicted_intent),
            "modelConfidence": float(confidence),
            "action": "upload_image" if final_intent in {"image_request", "image_followup", "awaiting_image"} or (final_intent == 'image_explanation' and self.conversation.get('last_image_status') == 'rejected') else None,
            "followUps": followups,
        }, pending)

    # ==============================================================
    # UPDATE CONVERSATION MEMORY
    # ==============================================================

    def update_conversation(self, intent, message):

        text = normalize_message(message)
        words = message_words(text)

        # A screening answer can contain symptoms as well as its primary field.
        symptom_words = SYMPTOM_WORDS
        if intent in {"location", "duration", "severity", "medication", "image_request"} and words & symptom_words:
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

        severity_words = {
            "mild",
            "moderate",
            "severe",
            "bad",
            "worse",
            "worst",
            "painful",
            "pain",
            "hurts",
            "hurt",
            "unbearable",
            "intense",
            "serious",
        }

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

        if has_location and intent != "location":
            self.conversation.set(
                "location",
                message
            )

        if has_duration and intent not in {"duration", "medication"}:
            self.conversation.set(
                "duration",
                message
            )

        if has_severity and intent != "severity":
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


    def get_knowledge_response(self, message, expected_intent):

        parsed = self.knowledge.parse_question(message)

        disease = parsed["disease"]
        topics = parsed["topics"]
        from_photo = False

        # ----------------------------------------------------------
        # USE PREVIOUS KNOWLEDGE CONTEXT
        # ----------------------------------------------------------

        if disease is None:
            previous_disease = self.conversation.get(
                "knowledge_disease"
            )
            if self.conversation.get('last_image_status') == 'rejected' and (not self.conversation.get('last_knowledge_topics') or message_words(message) & {'photo', 'picture', 'image', 'result'}):
                return "I couldn't reliably classify the latest photo, so I can't use it to suggest condition-specific care. You can ask about the rejection, send another photo, or name a condition for general information."
            if is_disease_overview_question(message) and self.conversation.get('classification') and (previous_disease is None or message_words(message) & {'photo', 'picture', 'image', 'result'}):
                disease = self.image_knowledge_disease()
                from_photo = True
            elif previous_disease is not None:
                disease = previous_disease
                from_photo = disease == self.image_knowledge_disease()
            elif self.conversation.get('classification') == 'normal_skin':
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

        if disease == 'normal_skin':
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
        labels = {'symptoms': 'Symptoms', 'causes': 'Causes', 'contagious': 'Spreading to others', 'management': 'General care', 'referral': 'Getting professional help', 'overview': 'Overview'}
        answers = []
        for topic in topics:
            knowledge = self.knowledge.get(disease, topic)
            if knowledge:
                if dialogue_act(message) == 'simple_explanation':
                    knowledge = concise(knowledge)
                answers.append(f'{labels[topic]}: {knowledge}' if len(topics) > 1 else knowledge)
        if not answers:
            return "I don't have enough information in my knowledge base to answer that accurately. You can ask about symptoms, causes, general care, or getting the condition checked."
        answer = f"General information about {self.knowledge.data[disease]['name']}:\n\n" + '\n\n'.join(answers)
        if from_photo:
            answer = "I'm explaining your photo model's screening suggestion, not a confirmed diagnosis.\n\n" + answer
        if is_medication_question(message):
            answer = "I can't choose a medicine or dose from a chat or screening photo. " + answer
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

        next_question = self.flow.next_question(
            self.conversation
        )

        if acknowledgement:
            return f"{acknowledgement} {next_question}"

        return next_question

    def handle_correction(self, message):
        updates = correction_updates(message)
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
