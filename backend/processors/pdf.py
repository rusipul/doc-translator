import io
import fitz  # PyMuPDF


def extract_texts(file_bytes: bytes) -> list[dict]:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
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
    doc.close()
    if not segments:
        raise ValueError("텍스트가 없는 PDF입니다. 스캔본 PDF는 지원되지 않습니다.")
    return segments


def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    raise NotImplementedError
