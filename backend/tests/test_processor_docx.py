import io
from docx import Document
from processors.docx import extract_texts, reinsert_texts

def _make_docx(texts: list[str]) -> bytes:
    doc = Document()
    for t in texts:
        doc.add_paragraph(t)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def test_extract_texts():
    data = _make_docx(["안녕하세요", "테스트입니다"])
    segments = extract_texts(data)
    assert [s["text"] for s in segments] == ["안녕하세요", "테스트입니다"]

def test_reinsert_texts():
    data = _make_docx(["안녕하세요"])
    segments = extract_texts(data)
    translated = ["Hello"]
    result = reinsert_texts(data, segments, translated)
    doc = Document(io.BytesIO(result))
    assert doc.paragraphs[0].text == "Hello"

def test_empty_runs_skipped():
    data = _make_docx([""])
    segments = extract_texts(data)
    assert all(s["text"] != "" for s in segments)
