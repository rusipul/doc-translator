import io, os
os.environ["SHARED_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

def _login():
    assert client.post("/auth/login", json={"password": "testpass"}).status_code == 200

def _make_docx_bytes() -> bytes:
    from docx import Document
    doc = Document()
    doc.add_paragraph("안녕하세요")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def test_translate_docx():
    _login()
    with patch("config.get_api_key", return_value="fake-key"), \
         patch("translate.batch_translate", return_value=["Hello"]):
        res = client.post(
            "/translate",
            files={"file": ("test.docx", _make_docx_bytes(),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"target_lang": "en"},
        )
    assert res.status_code == 200
    assert res.headers["content-disposition"].endswith('.docx"')

def test_translate_no_api_key():
    _login()
    with patch("config.get_api_key", return_value=None):
        res = client.post(
            "/translate",
            files={"file": ("test.docx", _make_docx_bytes(),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"target_lang": "en"},
        )
    assert res.status_code == 503

def test_translate_unsupported_format():
    _login()
    res = client.post(
        "/translate",
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"target_lang": "en"},
    )
    assert res.status_code == 400
