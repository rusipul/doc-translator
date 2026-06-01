import pytest
from unittest.mock import patch, MagicMock
from translate import batch_translate, TranslateError

def test_batch_translate_returns_translated_texts():
    mock_client = MagicMock()
    mock_response = [
        {"translatedText": "Hello"},
        {"translatedText": "World"},
    ]
    mock_client.translate.return_value = mock_response

    with patch("translate._make_client", return_value=mock_client):
        result = batch_translate(["안녕", "세계"], target_lang="en", api_key="fake")

    assert result == ["Hello", "World"]

def test_batch_translate_empty_list():
    result = batch_translate([], target_lang="en", api_key="fake")
    assert result == []

def test_batch_translate_raises_on_api_error():
    mock_client = MagicMock()
    mock_client.translate.side_effect = Exception("API error")

    with patch("translate._make_client", return_value=mock_client):
        with pytest.raises(TranslateError):
            batch_translate(["텍스트"], target_lang="en", api_key="fake")
