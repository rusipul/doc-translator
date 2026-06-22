import io
from docx import Document


def _iter_table_runs(table, base_key: tuple):
    """Yield (run, key) for all runs in a table, recursing into nested tables."""
    # Keep strong references to _tc proxies so lxml doesn't GC them.
    # Using id() is unreliable: freed proxy addresses get reused for unrelated cells.
    seen_tcs: set = set()
    for ri, row in enumerate(table.rows):
        for ci, cell in enumerate(row.cells):
            if cell._tc in seen_tcs:
                continue
            seen_tcs.add(cell._tc)
            cell_key = (*base_key, ri, ci)
            for pi, para in enumerate(cell.paragraphs):
                for ji, run in enumerate(para.runs):
                    yield run, (*cell_key, pi, ji)
            for nti, nested_table in enumerate(cell.tables):
                yield from _iter_table_runs(nested_table, (*cell_key, nti))


def _iter_runs(doc: Document):
    """Yield (run, key) for all runs in body paragraphs and tables."""
    for i, para in enumerate(doc.paragraphs):
        for j, run in enumerate(para.runs):
            yield run, ("para", i, j)
    for ti, table in enumerate(doc.tables):
        yield from _iter_table_runs(table, ("table", ti))


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
