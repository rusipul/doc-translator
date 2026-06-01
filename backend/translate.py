from google.cloud import translate_v2 as gtranslate

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

    client = _make_client(api_key)
    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        for attempt in range(2):
            try:
                kwargs: dict = {"target_language": target_lang, "values": chunk}
                if source_lang:
                    kwargs["source_language"] = source_lang
                response = client.translate(**kwargs)
                results.extend(r["translatedText"] for r in response)
                break
            except Exception as e:
                if attempt == 1:
                    raise TranslateError(str(e)) from e

    return results
