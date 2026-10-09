"""
Retrieval layer: embeds the knowledge base once at startup, then does
semantic search against it for each incoming question.

This is the "R" in RAG. It never talks to the LLM -- it just finds the
most relevant KB chunks for a question.
"""

from threading import Lock

# Single source of truth: the SAME dict your Flask app already uses to
# render the "Prediction Breakdown" UI. We extend it (see condition_info.py)
# with chatbot-facing fields instead of maintaining a second copy.
from chatbot.knowledge_base import CONDITION_INFO, APP_FAQ

_MODEL_NAME = "all-MiniLM-L6-v2"
_SCORE_THRESHOLD = 0.35  # tune this after testing; below this, treat as "no good match"

# Fields pulled into the chatbot's retrieval corpus. "summary" and "why" are
# deliberately excluded -- those describe the CNN's own reasoning, not facts
# about the disease, and would confuse answers to disease questions.
_RETRIEVABLE_FIELDS = ["description", "symptoms", "triggers", "appearance", "recommendations", "seek_help"]

# Sentinel used in place of "condition" for app-FAQ chunks (how Flamma
# works, upload guidance, trust, privacy). condition_hint filtering only
# ever matches real condition names, so these always stay eligible
# regardless of which condition (if any) was just classified.
_APP_FAQ_TAG = "_app_faq"

_model = None
_corpus_texts = []      # flat list of "field: text" strings
_corpus_meta = []       # parallel list of (condition, field) tuples
_corpus_embeddings = None
_init_lock = Lock()


def _flatten_kb():
    """Turn CONDITION_INFO + APP_FAQ into flat (condition, field, text) chunks."""
    texts, meta = [], []

    for condition, fields in CONDITION_INFO.items():
        for field in _RETRIEVABLE_FIELDS:
            text = fields.get(field)
            if not text:
                continue
            # Prefix with condition + field so the embedding captures context,
            # e.g. "psoriasis triggers: Stress, skin injury..."
            texts.append(f"{condition.replace('_', ' ')} {field}: {text}")
            meta.append((condition, field, text))

    for topic, text in APP_FAQ.items():
        texts.append(f"Flamma app {topic.replace('_', ' ')}: {text}")
        meta.append((_APP_FAQ_TAG, topic, text))

    return texts, meta


def init_retriever():
    """Load retrieval only when the optional chat endpoint needs it."""
    global _model, _corpus_texts, _corpus_meta, _corpus_embeddings
    with _init_lock:
        if _corpus_embeddings is not None:
            return
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(_MODEL_NAME)
        texts, meta = _flatten_kb()
        embeddings = model.encode(texts, convert_to_tensor=True)
        _model, _corpus_texts, _corpus_meta, _corpus_embeddings = model, texts, meta, embeddings


def retrieve(query: str, top_k: int = 2, condition_hint: str | None = None):
    """
    Return the top_k most relevant KB chunks for the query.

    condition_hint: if given (e.g. the CNN's predicted class), results are
    filtered to that condition OR app-FAQ chunks -- so "what triggers this?"
    after an image upload stays scoped to the classified condition instead
    of matching triggers from a different disease, while app-level
    questions ("how does Flamma work?") still always match regardless.

    Returns a list of dicts: {"condition", "field", "text", "score"}.
    Empty list means nothing matched well enough -- caller should NOT
    call the LLM in that case (see chat_service.py).
    """
    if _corpus_embeddings is None:
        init_retriever()
    from sentence_transformers import util

    query_embedding = _model.encode(query, convert_to_tensor=True)
    hits = util.semantic_search(query_embedding, _corpus_embeddings, top_k=top_k * 3)[0]

    results = []
    for hit in hits:
        condition, field, text = _corpus_meta[hit["corpus_id"]]
        if condition_hint and condition != condition_hint and condition != _APP_FAQ_TAG:
            continue
        if hit["score"] < _SCORE_THRESHOLD:
            continue
        results.append({
            "condition": condition,
            "field": field,
            "text": text,
            "score": float(hit["score"]),
        })
        if len(results) >= top_k:
            break

    return results
