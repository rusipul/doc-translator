import io
from pptx import Presentation


def extract_texts(file_bytes: bytes) -> list[dict]:
    prs = Presentation(io.BytesIO(file_bytes))
    segments = []
    for si, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            shape_id = shape.shape_id  # stable XML attribute, not positional index
            for pi, para in enumerate(shape.text_frame.paragraphs):
                for ri, run in enumerate(para.runs):
                    if run.text.strip():
                        segments.append({
                            "text": run.text,
                            "key": (si, shape_id, pi, ri),
                        })
    return segments


def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    prs = Presentation(io.BytesIO(file_bytes))
    key_to_translation = {
        tuple(s["key"]): t for s, t in zip(segments, translated)
    }
    for si, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            shape_id = shape.shape_id
            for pi, para in enumerate(shape.text_frame.paragraphs):
                for ri, run in enumerate(para.runs):
                    key = (si, shape_id, pi, ri)
                    if key in key_to_translation:
                        run.text = key_to_translation[key]
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
