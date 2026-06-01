import io
from pptx import Presentation
from pptx.util import Inches
from processors.pptx import extract_texts, reinsert_texts

def _make_pptx(texts: list[str]) -> bytes:
    prs = Presentation()
    layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(layout)
    for text in texts:
        txBox = slide.shapes.add_textbox(Inches(1), Inches(1), Inches(4), Inches(1))
        txBox.text_frame.text = text
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()

def test_extract_texts():
    data = _make_pptx(["안녕하세요", "테스트"])
    segments = extract_texts(data)
    texts = [s["text"] for s in segments]
    assert "안녕하세요" in texts
    assert "테스트" in texts

def test_reinsert_texts():
    data = _make_pptx(["안녕하세요"])
    segments = extract_texts(data)
    result = reinsert_texts(data, segments, ["Hello"])
    prs = Presentation(io.BytesIO(result))
    all_texts = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                all_texts.append(shape.text_frame.text)
    assert "Hello" in all_texts
