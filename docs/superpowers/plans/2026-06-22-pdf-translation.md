# PDF 번역 지원 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PyMuPDF를 사용해 텍스트 기반 PDF 파일의 번역을 지원한다 — 원본 레이아웃을 최대한 유지하면서 PDF로 반환.

**Architecture:** 기존 `extract_texts` / `reinsert_texts` 인터페이스를 그대로 따르는 `processors/pdf.py` 모듈을 추가한다. extract는 페이지→블록→라인→스팬을 순회해 텍스트를 수집하고, reinsert는 원본 스팬 위치를 흰 사각형으로 덮은 뒤 CJK 폰트로 번역 텍스트를 삽입한다.

**Tech Stack:** PyMuPDF(fitz) ≥ 1.24.0, 기존 FastAPI 백엔드, React 프론트엔드

---

## 파일 구성

| 파일 | 역할 |
|------|------|
| `backend/requirements.txt` | `pymupdf` 의존성 추가 |
| `backend/processors/pdf.py` | `extract_texts`, `reinsert_texts` 구현 |
| `backend/tests/test_processor_pdf.py` | 단위 테스트 |
| `backend/routers/translate_router.py` | `pdf` 엔트리 추가 |
| `frontend/src/pages/Translate.tsx` | `.pdf` 허용 확장자 추가 |

---

## Task 1: pymupdf 설치

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: requirements.txt에 pymupdf 추가**

```text
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
python-docx==1.1.2
openpyxl==3.1.2
python-pptx==0.6.23
python-dotenv==1.0.1
pymupdf>=1.24.0
```

- [ ] **Step 2: 패키지 설치**

```bash
cd backend
.venv/Scripts/pip install pymupdf
```

Expected: `Successfully installed pymupdf-...`

- [ ] **Step 3: 설치 확인**

```bash
.venv/Scripts/python -c "import fitz; print(fitz.__version__)"
```

Expected: 버전 번호 출력 (예: `1.24.11`)

- [ ] **Step 4: 커밋**

```bash
git add backend/requirements.txt
git commit -m "chore: add pymupdf dependency for PDF translation"
```

---

## Task 2: extract_texts 구현 (TDD)

**Files:**
- Create: `backend/tests/test_processor_pdf.py`
- Create: `backend/processors/pdf.py`

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/test_processor_pdf.py`:

```python
import io
import pytest
import fitz
from processors.pdf import extract_texts


def _make_pdf(texts: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    y = 72
    for text in texts:
        page.insert_text((72, y), text, fontname="cjk", fontsize=12)
        y += 20
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend
.venv/Scripts/python -m pytest tests/test_processor_pdf.py -v
```

Expected: `ModuleNotFoundError: No module named 'processors.pdf'`

- [ ] **Step 3: extract_texts 구현**

`backend/processors/pdf.py`:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
.venv/Scripts/python -m pytest tests/test_processor_pdf.py::test_extract_texts tests/test_processor_pdf.py::test_extract_keys_are_unique -v
```

Expected: `2 passed`

- [ ] **Step 5: 커밋**

```bash
git add backend/processors/pdf.py backend/tests/test_processor_pdf.py
git commit -m "feat: add PDF extract_texts with PyMuPDF"
```

---

## Task 3: reinsert_texts 구현 (TDD)

**Files:**
- Modify: `backend/tests/test_processor_pdf.py`
- Modify: `backend/processors/pdf.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`test_processor_pdf.py` 상단의 import를 수정하고, 테스트 함수를 하단에 추가:

```python
# 파일 상단 import 줄 변경 (extract_texts → extract_texts, reinsert_texts)
from processors.pdf import extract_texts, reinsert_texts
```

이후 파일 하단에 추가:

```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/Scripts/python -m pytest tests/test_processor_pdf.py::test_reinsert_texts -v
```

Expected: `NotImplementedError`

- [ ] **Step 3: reinsert_texts 구현**

`backend/processors/pdf.py`의 `reinsert_texts`를 교체:

```python
def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    doc = fitz.open(stream=file_bytes, filetype="pdf")
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
                    fontname="cjk",
                    fontsize=item["size"],
                )
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()
```

- [ ] **Step 4: 전체 테스트 통과 확인**

```bash
.venv/Scripts/python -m pytest tests/test_processor_pdf.py -v
```

Expected: `4 passed`

- [ ] **Step 5: 커밋**

```bash
git add backend/processors/pdf.py backend/tests/test_processor_pdf.py
git commit -m "feat: add PDF reinsert_texts with redact-and-insert approach"
```

---

## Task 4: 스캔본 PDF 에러 처리 테스트

**Files:**
- Modify: `backend/tests/test_processor_pdf.py`

- [ ] **Step 1: 실패하는 테스트 추가**

`test_processor_pdf.py` 하단에 추가:

```python
def _make_image_only_pdf() -> bytes:
    """텍스트 없이 빈 페이지만 있는 PDF (스캔본 시뮬레이션)."""
    doc = fitz.open()
    doc.new_page()
    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def test_image_only_pdf_raises_value_error():
    data = _make_image_only_pdf()
    with pytest.raises(ValueError, match="텍스트가 없는 PDF"):
        extract_texts(data)
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
.venv/Scripts/python -m pytest tests/test_processor_pdf.py::test_image_only_pdf_raises_value_error -v
```

Expected: `FAILED` (ValueError가 아직 안 맞는 조건 가능) 또는 이미 구현됐으면 `PASSED`

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
.venv/Scripts/python -m pytest tests/test_processor_pdf.py -v
```

Expected: `5 passed`

- [ ] **Step 4: 커밋**

```bash
git add backend/tests/test_processor_pdf.py
git commit -m "test: add image-only PDF ValueError test"
```

---

## Task 5: 라우터에 pdf 엔트리 추가

**Files:**
- Modify: `backend/routers/translate_router.py`

- [ ] **Step 1: import 및 PROCESSORS 수정**

`backend/routers/translate_router.py`의 기존 import 블록 아래에 추가하고 PROCESSORS 딕셔너리를 수정:

```python
# 기존 import에 아래 한 줄 추가
from processors import pdf as pdf_proc

# PROCESSORS 딕셔너리에 pdf 엔트리 추가
PROCESSORS = {
    "docx": (
        docx_proc.extract_texts,
        docx_proc.reinsert_texts,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ),
    "xlsx": (
        xlsx_proc.extract_texts,
        xlsx_proc.reinsert_texts,
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    "pptx": (
        pptx_proc.extract_texts,
        pptx_proc.reinsert_texts,
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    "pdf": (
        pdf_proc.extract_texts,
        pdf_proc.reinsert_texts,
        "application/pdf",
    ),
}
```

- [ ] **Step 2: 엔드포인트 테스트 — 서버 기동 확인**

```bash
cd backend
.venv/Scripts/python -m pytest tests/ -v --ignore=tests/test_translate_endpoint.py
```

Expected: 모든 테스트 통과

- [ ] **Step 3: 커밋**

```bash
git add backend/routers/translate_router.py
git commit -m "feat: register PDF processor in translate router"
```

---

## Task 6: 프론트엔드 파일 허용 목록 업데이트

**Files:**
- Modify: `frontend/src/pages/Translate.tsx`

- [ ] **Step 1: 세 곳 수정**

`frontend/src/pages/Translate.tsx`에서 아래 세 부분을 수정:

```tsx
// 1. 허용 확장자 집합
const ALLOWED_EXTS = new Set(['.docx', '.xlsx', '.pptx', '.pdf'])

// 2. 에러 메시지
setErrorMsg('.docx, .xlsx, .pptx, .pdf 파일만 지원합니다')

// 3. input accept 속성 및 안내 텍스트
<input ref={inputRef} type="file" accept=".docx,.xlsx,.pptx,.pdf" hidden
  onChange={e => { const f = e.target.files?.[0]; if (f) applyFile(f) }} />
...
<p style={{ color: '#888', fontSize: 12 }}>.docx · .xlsx · .pptx · .pdf · 최대 20MB</p>
```

- [ ] **Step 2: 커밋**

```bash
git add frontend/src/pages/Translate.tsx
git commit -m "feat: allow PDF file upload in frontend"
```

---

## Task 7: GitHub 푸시

- [ ] **Step 1: 전체 테스트 최종 확인**

```bash
cd backend
.venv/Scripts/python -m pytest tests/ -v --ignore=tests/test_translate_endpoint.py
```

Expected: 모든 테스트 통과

- [ ] **Step 2: 푸시**

```bash
git push origin main
```

Expected: `main -> main` 푸시 완료 후 Render 자동 배포 시작
