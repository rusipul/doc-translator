import pytest
from unittest.mock import patch
from translate import batch_translate, TranslateError


def test_batch_translate_returns_translated_texts():
    mock_response = {
        "data": {
            "translations": [
                {"translatedText": "Hello"},
                {"translatedText": "World"},
            ]
        }
    }
    with patch("translate._call_api", return_value=mock_response):
        result = batch_translate(["안녕", "세계"], target_lang="en", api_key="fake")

    assert result == ["Hello", "World"]


def test_batch_translate_empty_list():
    result = batch_translate([], target_lang="en", api_key="fake")
    assert result == []


def test_batch_translate_raises_on_api_error():
    with patch("translate._call_api", side_effect=Exception("API error")):
        with pytest.raises(TranslateError):
            batch_translate(["텍스트"], target_lang="en", api_key="fake")
