import json
from openai import OpenAI

BATCH_SIZE = 50

_LANG_NAMES = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese (Simplified)",
    "ko": "Korean",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "vi": "Vietnamese",
}


class TranslateError(Exception):
    pass


def batch_translate(
    texts: list[str],
    target_lang: str,
    api_key: str,
    source_lang: str | None = None,
) -> list[str]:
    if not texts:
        return []
    if not api_key:
        raise TranslateError("API key is not set")

    lang_name = _LANG_NAMES.get(target_lang, target_lang)
    client = OpenAI(api_key=api_key)
    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i: i + BATCH_SIZE]

        # Use numbered keys so the model cannot merge or skip items
        numbered = {str(j): text for j, text in enumerate(chunk)}
        prompt = (
            f"Translate the following texts to {lang_name}. "
            "The input is a JSON object where keys are numeric indices and values are texts to translate. "
            "Return a JSON object with the same numeric keys and translated strings as values. "
            "Every key must be present in the output. Do not add explanations.\n\n"
            f"Input: {json.dumps(numbered, ensure_ascii=False)}"
        )

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Translate accurately and naturally, preserving the original meaning and tone."},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )
                body = json.loads(response.choices[0].message.content)
                # Reconstruct in original order by numeric key
                translated = [body[str(j)] for j in range(len(chunk))]
                results.extend(translated)
                last_exc = None
                break
            except (KeyError, TypeError) as e:
                last_exc = TranslateError(f"Unexpected response format: {e}")
            except Exception as e:
                last_exc = e

        if last_exc is not None:
            raise TranslateError(str(last_exc)) from last_exc

    return results
