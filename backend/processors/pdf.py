import io
import fitz  # PyMuPDF


def extract_texts(file_bytes: bytes) -> list[dict]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        segments = []
        for pi, page in enumerate(doc):
            for bi, block in enumerate(page.get_text("dict")["blocks"]):
                if block.get("type") != 0:
                    continue
                for li, line in enumerate(block["lines"]):
                    for si, span in enumerate(line["spans"]):
                        text = span["text"].strip()
                        if text:
                            segments.append({
                                "text": text,
                                "key": (pi, bi, li, si),
                            })
    finally:
        doc.close()
    if not segments:
        raise ValueError("텍스트가 없는 PDF입니다. 스캔본 PDF는 지원되지 않습니다.")
    return segments


def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        key_to_translation = {
            tuple(s["key"]): t for s, t in zip(segments, translated)
        }
        for pi, page in enumerate(doc):
            inserts = []
            for bi, block in enumerate(page.get_text("dict")["blocks"]):
                if block.get("type") != 0:
                    continue
                for li, line in enumerate(block["lines"]):
                    for si, span in enumerate(line["spans"]):
                        key = (pi, bi, li, si)
                        if key in key_to_translation:
                            inserts.append({
                                "bbox": fitz.Rect(span["bbox"]),
                                "text": key_to_translation[key],
                                "size": span["size"],
                                "origin": span["origin"],
                            })
            if inserts:
                for item in inserts:
                    page.add_redact_annot(item["bbox"], fill=(1, 1, 1))
                page.apply_redactions()
                for item in inserts:
                    page.insert_text(
                        item["origin"],
                        item["text"],
                        fontname="helv",
                        fontsize=item["size"],
                    )
        buf = io.BytesIO()
        doc.save(buf)
    finally:
        doc.close()
    return buf.getvalue()
