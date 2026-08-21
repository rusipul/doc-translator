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
                    # Merge all spans in a line into one segment so the AI
                    # sees the full phrase (e.g. "数字输入D类音频播放器")
                    # instead of tiny fragments that lose translation context.
                    spans = line["spans"]
                    text = "".join(s["text"] for s in spans).strip()
                    if not text:
                        continue
                    segments.append({
                        "text": text,
                        "key": (pi, bi, li),
                        # Store per-span details for reinsertion
                        "_spans": [
                            {
                                "bbox": fitz.Rect(s["bbox"]),
                                "origin": s["origin"],
                                "size": s["size"],
                            }
                            for s in spans
                            if s["text"].strip()
                        ],
                    })
    finally:
        doc.close()
    if not segments:
        raise ValueError("텍스트가 없는 PDF입니다. 스캔본 PDF는 지원되지 않습니다.")
    return segments


def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        key_to_seg = {tuple(s["key"]): (s, t) for s, t in zip(segments, translated)}

        for pi, page in enumerate(doc):
            page_inserts = []
            for bi, block in enumerate(page.get_text("dict")["blocks"]):
                if block.get("type") != 0:
                    continue
                for li, line in enumerate(block["lines"]):
                    key = (pi, bi, li)
                    if key not in key_to_seg:
                        continue
                    seg, translation = key_to_seg[key]
                    spans = seg["_spans"]
                    if not spans:
                        continue
                    page_inserts.append({
                        "spans": spans,
                        "text": translation,
                        "size": spans[0]["size"],
                        "origin": spans[0]["origin"],
                    })

            if not page_inserts:
                continue

            # Redact all original span bboxes
            for item in page_inserts:
                for sp in item["spans"]:
                    page.add_redact_annot(sp["bbox"], fill=(1, 1, 1))
            page.apply_redactions()

            # Insert translated text at the first span's origin using CJK font
            cjk_font = fitz.Font("cjk")
            tw = fitz.TextWriter(page.rect)
            for item in page_inserts:
                try:
                    tw.append(
                        fitz.Point(item["origin"]),
                        item["text"],
                        font=cjk_font,
                        fontsize=item["size"],
                    )
                except Exception:
                    page.insert_text(
                        item["origin"],
                        item["text"],
                        fontname="helv",
                        fontsize=item["size"],
                    )
            tw.write_text(page)

        buf = io.BytesIO()
        doc.save(buf)
    finally:
        doc.close()
    return buf.getvalue()
