import html
from google.cloud import translate_v2 as gtranslate

# Google Translate v2 maximum strings per request
BATCH_SIZE = 128


class TranslateError(Exception):
    pass


def _make_client(api_key: str):
    return gtranslate.Client(client_options={"api_key": api_key})


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

    client = _make_client(api_key)
    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                kwargs: dict = {"target_language": target_lang, "values": chunk}
                if source_lang:
                    kwargs["source_language"] = source_lang
                response = client.translate(**kwargs)
                # Google Translate v2 returns HTML-escaped text; decode it
                results.extend(html.unescape(r["translatedText"]) for r in response)
                last_exc = None
                break
            except Exception as e:
                last_exc = e
        if last_exc is not None:
            raise TranslateError(str(last_exc)) from last_exc

    return results
