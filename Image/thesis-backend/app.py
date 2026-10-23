import os
from pathlib import Path
from threading import Lock

from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageOps

from inference.classifier import MODEL_INFO, predict
from inference.skin_detector import looks_like_skin
from inference.condition_info import CONDITION_INFO
from inference.blur_check import blur_status

# ============================================================
# APP SETUP
# ============================================================

app = Flask(__name__)
CORS(app)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
# The crop heatmaps share activation/gradient hooks on the loaded model.
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
    return jsonify(status='ok', service='flamma-image', pid=os.getpid(),
                   app_path=str(Path(__file__).resolve()), model=MODEL_INFO)


@app.errorhandler(413)
def upload_too_large(error):
    return jsonify(status='rejected', reason='too_large',
                   message='Please upload an image smaller than 10 MB.'), 413


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
        with Image.open(image_file.stream) as uploaded:
            image = ImageOps.exif_transpose(uploaded).convert('RGB')
    except Exception:
        return jsonify({
            "status": "rejected",
            "reason": "default"
        }), 400

    # ========================================================
    # STAGE 0: BLUR CHECK
    # ========================================================

    blur_state, blur = blur_status(image)
    quality = {'blur_status': blur_state, 'blur_score': round(float(blur), 2)}
    print(f"[blur] score={blur:.1f} status={blur_state}")

    if blur_state == "blocked":
        return jsonify({
            "status": "rejected",
            "reason": "too_blurry",
            "quality": quality,
        }), 400

    # ========================================================
    # STAGE 1: SKIN CONTENT SCREENING
    # ========================================================

    if not looks_like_skin(image):
        return jsonify({
            "status": "rejected",
            "reason": "no_skin_detected",
            "quality": quality,
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
            "quality": quality,
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
            "quality": quality,
        })

    class_name = result["predicted_class"]

    # Genuinely uncertain prediction, regardless of which class won
    if not result["is_confident"]:
        return jsonify({
            "status": "rejected",
            "reason": "low_confidence",
            "quality": quality,
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
        "quality": quality,
    })

# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    app.run(
        debug=os.environ.get('FLAMMA_DEBUG') == '1',
        host="127.0.0.1",
        port=8000
    )
