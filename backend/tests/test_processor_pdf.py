import io
import pytest
import fitz
from processors.pdf import extract_texts, reinsert_texts


def _make_pdf(texts: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    font = fitz.Font(fontfile="C:/Windows/Fonts/malgun.ttf")  # Windows-only; tests not expected to run in CI
    tw = fitz.TextWriter(page.rect)
    y = 72
    for text in texts:
        tw.append((72, y), text, font=font, fontsize=12)
        y += 20
    tw.write_text(page)
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_extract_texts():
    data = _make_pdf(["안녕하세요", "테스트"])
    segments = extract_texts(data)
    texts = [s["text"] for s in segments]
    assert "안녕하세요" in texts
    assert "테스트" in texts


def test_extract_keys_are_unique():
    data = _make_pdf(["첫번째", "두번째", "세번째"])
    segments = extract_texts(data)
    keys = [tuple(s["key"]) for s in segments]
    assert len(keys) == len(set(keys))


def test_reinsert_texts():
    data = _make_pdf(["안녕하세요"])
    segments = extract_texts(data)
    result = reinsert_texts(data, segments, ["Hello"])
    doc = fitz.open(stream=result, filetype="pdf")
    all_text = "".join(page.get_text() for page in doc)
    doc.close()
    assert "Hello" in all_text


def test_reinsert_preserves_page_count():
    data = _make_pdf(["페이지1"])
    segments = extract_texts(data)
    result = reinsert_texts(data, segments, ["Page1"])
    original_doc = fitz.open(stream=data, filetype="pdf")
    result_doc = fitz.open(stream=result, filetype="pdf")
    assert len(result_doc) == len(original_doc)
    original_doc.close()
    result_doc.close()
