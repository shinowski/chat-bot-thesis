from flask import Flask, render_template, request, jsonify
from model.semantic_chatbot import SemanticChatbot

bot = SemanticChatbot()

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():

    # --------------------------------
    # GET TEXT MESSAGE
    # --------------------------------
    message = request.form.get("message", "").strip()

    # --------------------------------
    # GET IMAGE
    # --------------------------------
    image = request.files.get("image")

    # --------------------------------
    # IMAGE UPLOAD
    # --------------------------------
    if image:
        print("\n========== IMAGE RECEIVED ==========")
        print("Filename:", image.filename)
        print("Content type:", image.content_type)
        print("Size:", image.content_length)
        print("====================================\n")

        result = bot.reply(
            message,
            image=image
        )

        return jsonify(result)

    # --------------------------------
    # TEXT-ONLY MESSAGE
    # --------------------------------
    if not message:
        return jsonify({
            "reply": "Please describe your skin concern or upload an image.",
            "intent": "unknown",
            "confidence": 0.0,
            "followUps": []
        })

    result = bot.reply(message)

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)