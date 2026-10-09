import os

from chatbot.prompts import SYSTEM_PROMPT


_client = None
_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")


def _get_client():
    global _client

    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY environment variable is not set"
            )

        try:
            from google import genai
        except ImportError as error:
            raise RuntimeError("Install requirements-chat.txt to use Gemini chat.") from error

        _client = genai.Client(api_key=api_key)

    return _client


def generate_response(user_prompt: str) -> str:
    client = _get_client()
    from google.genai import types

    response = client.models.generate_content(
        model=_MODEL,
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            max_output_tokens=300,
            # Gemini 3.x defaults to dynamic/high thinking, which adds
            # latency and cost we don't need here -- this task is just
            # rephrasing retrieved KB text, not multi-step reasoning.
            # (temperature/top_p/top_k are deprecated on 3.x, so this
            # replaces the "low temperature = stay grounded" role they
            # used to play.)
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )

    if not response.text:
        raise RuntimeError("Gemini returned an empty response.")

    return response.text.strip()
