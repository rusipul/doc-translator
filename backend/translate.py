import html
import json
import urllib.request
import urllib.error

# Google Translate v2 maximum strings per request
BATCH_SIZE = 128
_API_URL = "https://translation.googleapis.com/language/translate/v2"


class TranslateError(Exception):
    pass


def _call_api(api_key: str, payload: dict) -> dict:
    url = f"{_API_URL}?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


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

    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        payload: dict = {"q": chunk, "target": target_lang, "format": "text"}
        if source_lang:
            payload["source"] = source_lang

        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                body = _call_api(api_key, payload)
                translations = body["data"]["translations"]
                # Google Translate v2 returns HTML-escaped text; decode it
                results.extend(html.unescape(t["translatedText"]) for t in translations)
                last_exc = None
                break
            except urllib.error.HTTPError as e:
                err_body = e.read().decode(errors="replace")
                last_exc = TranslateError(f"HTTP {e.code}: {err_body}")
            except Exception as e:
                last_exc = e

        if last_exc is not None:
            raise TranslateError(str(last_exc)) from last_exc

    return results
