from flask import Flask, render_template, request, jsonify
from model.chatbot import Chatbot

bot = Chatbot()

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():

    message = request.json["message"]

    result = bot.reply(message)

    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)