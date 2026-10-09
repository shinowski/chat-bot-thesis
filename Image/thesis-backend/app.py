import os
from pathlib import Path
from math import isfinite

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
from threading import Lock

from inference.classifier import predict
from skin_detector import looks_like_skin
from chatbot.knowledge_base import CONDITION_INFO
from chatbot.chat_service import handle_chat, build_upload_greeting

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
# Grad-CAM stores activations and gradients on a shared model.
prediction_lock = Lock()

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# ============================================================
# ROUTES
# ============================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok", "service": "flamma-image", "pid": os.getpid(),
        "app_path": str(Path(__file__).resolve()),
    })


@app.route("/api/predict", methods=["POST"])
def predict_image():

    if "image" not in request.files:
        return jsonify({
            "status": "rejected",
            "reason": "default"
        }), 400

    image_file = request.files["image"]

    if image_file.filename == "":
        return jsonify({
            "status": "rejected",
            "reason": "default"
        }), 400

    if not allowed_file(image_file.filename):
        return jsonify({
            "status": "rejected",
            "reason": "default"
        }), 400

    # ========================================================
    # IMAGE VALIDATION
    # ========================================================

    try:
        image = Image.open(image_file.stream)
        image = image.convert("RGB")
    except Exception:
        return jsonify({
            "status": "rejected",
            "reason": "default"
        }), 400

    # ========================================================
    # STAGE 1: SKIN CONTENT SCREENING
    # ========================================================

    if not looks_like_skin(image):
        return jsonify({
            "status": "rejected",
            "reason": "no_skin_detected"
        }), 400

    # ========================================================
    # STAGE 2: MODEL PREDICTION
    # (includes OOD gate + normal-skin safety gate)
    # ========================================================

    with prediction_lock:
        result = predict(image)

    # ========================================================
    # STAGE 3: OOD / INCONCLUSIVE / CONFIDENCE CHECKS
    # ========================================================

    # OOD gate rejected it before classification even ran.
    if result["status"] == "outside_scope":
        return jsonify({
            "status": "rejected",
            "reason": "out_of_scope",
            "message": result["message"],
            "ood_score": result["ood_score"],
            "ood_threshold": result["ood_threshold"],
        }), 400

    # Model said "normal_skin" but failed the stricter normal-skin gate.
    # Has its own reason so the frontend can show an honest message
    # (not the "image too unclear" one). Extra fields are for
    # debugging/thesis metrics.
    if result["status"] == "inconclusive":
        return jsonify({
            "status": "rejected",
            "reason": "inconclusive",
            "message": result["message"],
            "inconclusive_reasons": result["inconclusive_reasons"],
            "normal_probability": result["normal_probability"],
            "crop_disease_max": result["crop_disease_max"],
        })

    class_name = result["predicted_class"]

    # Genuinely uncertain prediction, regardless of which class won
    if not result["is_confident"]:
        return jsonify({
            "status": "rejected",
            "reason": "low_confidence"
        })

    # ========================================================
    # CONDITION INFORMATION
    # ========================================================

    info = CONDITION_INFO.get(class_name, {
        "display_name": class_name.replace("_", " ").title(),
        "description": "No description available for this condition yet."
    })

    # ========================================================
    # RESPONSE
    # ========================================================

    return jsonify({
        **result,
        "status": "ok",
        "condition": info["display_name"],
        "description": info["description"],
        "summary": info.get("summary"),
        "why": info.get("why"),
        "recommendations": info.get("recommendations"),
        "chat_greeting": build_upload_greeting({
            "label": class_name,
            "confidence": result["confidence"],
        }),
    })

# ============================================================
# CHATBOT
# ============================================================


@app.route("/api/chat", methods=["POST"])
def chat():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be JSON."
        }), 400

    user_question = data.get("question", "")
    if not isinstance(user_question, str):
        return jsonify({"error": "Question must be text."}), 400
    user_question = user_question.strip()

    if not user_question:
        return jsonify({
            "error": "Question is required."
        }), 400

    # Optional CNN result from the frontend.
    #
    # Example:
    # {
    #     "label": "psoriasis",
    #     "confidence": 0.87
    # }
    cnn_result = data.get("cnn_result")
    if cnn_result is not None:
        if not isinstance(cnn_result, dict) or not isinstance(cnn_result.get('label'), str) or cnn_result['label'] not in CONDITION_INFO:
            return jsonify({"error": "The image-result label is invalid."}), 400
        confidence = cnn_result.get('confidence')
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not isfinite(confidence) or not 0 <= confidence <= 1:
            return jsonify({"error": "Image-result confidence must be between 0 and 1."}), 400

    # Flamma's local chatbot and image classifier do not require Gemini.
    # Only this optional endpoint uses it; avoid loading retrieval or the SDK
    # when cloud chat has not been configured.
    if not os.environ.get('GEMINI_API_KEY'):
        return jsonify({"error": "Gemini chat is not configured. Flamma's local chat and photo screening remain available."}), 503

    try:
        response = handle_chat(
            user_question=user_question,
            cnn_result=cnn_result
        )

        return jsonify({
            "response": response
        })

    except Exception as error:
        print(f"Chatbot error: {error}")

        return jsonify({
            "error": "The chatbot is temporarily unavailable."
        }), 500

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLAMMA_DEBUG") == "1",
        host="127.0.0.1",
        port=8000
    )
