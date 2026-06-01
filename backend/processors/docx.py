import io
from docx import Document


def _iter_runs(doc: Document):
    """Yield (run, location_key) for all runs in body paragraphs and tables.

    Merged table cells are deduplicated by tracking seen cell ids to avoid
    emitting the same cell's text multiple times.
    """
    for i, para in enumerate(doc.paragraphs):
        for j, run in enumerate(para.runs):
            yield run, ("para", i, j)
    for ti, table in enumerate(doc.tables):
        seen_cell_ids: set[int] = set()
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
                cell_id = id(cell._tc)
                if cell_id in seen_cell_ids:
                    continue
                seen_cell_ids.add(cell_id)
                for pi, para in enumerate(cell.paragraphs):
                    for ji, run in enumerate(para.runs):
                        yield run, ("table", ti, ri, ci, pi, ji)


def extract_texts(file_bytes: bytes) -> list[dict]:
    doc = Document(io.BytesIO(file_bytes))
    segments = []
    for run, key in _iter_runs(doc):
        if run.text.strip():
            segments.append({"text": run.text, "key": key})
    return segments


def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    doc = Document(io.BytesIO(file_bytes))
    key_to_translation = {
        tuple(s["key"]): t for s, t in zip(segments, translated)
    }
    for run, key in _iter_runs(doc):
        t = key_to_translation.get(tuple(key))
        if t is not None:
            run.text = t
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
