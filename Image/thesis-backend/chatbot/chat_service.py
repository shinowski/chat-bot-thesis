from chatbot.knowledge_base import CONDITION_INFO
from chatbot.retriever import retrieve
from chatbot.prompts import build_user_prompt
from chatbot.llm_client import generate_response

FALLBACK_MESSAGE = (
    "I don't have information on that. I can help with questions about "
    "Psoriasis, Lichen Planus, Rosacea, Atopic Dermatitis, and Contact Dermatitis, "
    "or Normal Skin -- or you can ask about your uploaded result. For anything "
    "else, it's best to check with a dermatologist."
)


def handle_chat(user_question: str, cnn_result: dict | None = None) -> str:
    """
    cnn_result (optional): {"label": "psoriasis", "confidence": 0.87}
    Passing this scopes retrieval to the classified condition, so follow-up
    questions like "what triggers this?" resolve correctly.
    """
    condition_hint = cnn_result.get("label") if cnn_result else None
    retrieved_chunks = retrieve(user_question, top_k=2, condition_hint=condition_hint)

    # Safety net: if retrieval found nothing relevant, don't call the LLM at
    # all -- return the fixed fallback instead of letting it freewheel on an
    # empty context.
    if not retrieved_chunks:
        return FALLBACK_MESSAGE

    user_prompt = build_user_prompt(user_question, retrieved_chunks, cnn_result)
    return generate_response(user_prompt)

def build_upload_greeting(cnn_result: dict) -> str | None:
    label = cnn_result.get("label")
    confidence = cnn_result.get("confidence", 0)
    info = CONDITION_INFO.get(label)
    if not info:
        return None

    if label == "normal_skin":
        return (
            "Thanks for uploading your photo! The image didn't match any of the "
            "conditions Flamma screens for, but this isn't a clinical clearance. "
            "Do you have any questions?"
        )

    return (
        f"Thanks for uploading your photo! It looks most similar to "
        f"{info['display_name']} ({confidence:.0%} pattern-match confidence). "
        f"This is a preliminary result, not a diagnosis. "
        f"Do you have any questions about it?"
    )