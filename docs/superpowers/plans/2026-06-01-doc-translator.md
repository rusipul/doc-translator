# Doc Translator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Word/Excel/PowerPoint 파일을 업로드하면 서식을 보존한 채 Google Translate API로 번역해 다운로드할 수 있는 팀 내부용 웹 서비스를 구축한다.

**Architecture:** Python FastAPI 백엔드(포트 8000)가 파일 처리·번역·인증을 담당하고, React 프론트엔드(포트 5173 개발 / Nginx 배포)가 UI를 제공한다. JWT HttpOnly 쿠키로 인증하며, Google API 키는 서버 측 `config.json`에 저장해 UI에서 즉시 교체 가능하다.

**Tech Stack:** Python 3.11, FastAPI, python-docx, openpyxl, python-pptx, google-cloud-translate, python-jose, React 18, TypeScript, Vite, Docker Compose

---

## File Map

| 파일 | 역할 |
|---|---|
| `backend/main.py` | FastAPI 앱 생성, 라우터 등록, CORS 설정 |
| `backend/auth.py` | 로그인 엔드포인트, JWT 발급·검증 의존성 |
| `backend/config.py` | `config.json` 읽기/쓰기, 설정 엔드포인트 |
| `backend/translate.py` | Google Translate API 배치 호출 래퍼 |
| `backend/processors/docx.py` | Word 텍스트 추출·재삽입 |
| `backend/processors/xlsx.py` | Excel 텍스트 추출·재삽입 |
| `backend/processors/pptx.py` | PowerPoint 텍스트 추출·재삽입 |
| `backend/routers/translate_router.py` | `POST /translate` 엔드포인트 |
| `backend/requirements.txt` | Python 의존성 |
| `backend/Dockerfile` | 백엔드 컨테이너 |
| `frontend/src/api.ts` | fetch 래퍼, 401 자동 리다이렉트 |
| `frontend/src/pages/Login.tsx` | 로그인 화면 |
| `frontend/src/pages/Translate.tsx` | 번역 메인·진행·완료 화면 |
| `frontend/src/pages/Settings.tsx` | API 키 설정 화면 |
| `frontend/src/App.tsx` | 라우터, 네비게이션 |
| `frontend/Dockerfile` | Nginx 프론트엔드 컨테이너 |
| `docker-compose.yml` | 전체 스택 오케스트레이션 |

---

## Task 1: 백엔드 프로젝트 초기화

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/main.py`

- [ ] **Step 1: requirements.txt 작성**

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
python-jose[cryptography]==3.3.0
python-docx==1.1.2
openpyxl==3.1.2
python-pptx==0.6.23
google-cloud-translate==3.15.3
httpx==0.27.0
pytest==8.2.0
pytest-asyncio==0.23.7
httpx==0.27.0
```

- [ ] **Step 2: 가상환경 생성 및 의존성 설치**

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Expected: 오류 없이 설치 완료

- [ ] **Step 3: main.py 작성**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Doc Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 4: 서버 기동 확인**

```bash
uvicorn main:app --reload --port 8000
```

브라우저에서 `http://localhost:8000/health` → `{"status":"ok"}` 확인

- [ ] **Step 5: 커밋**

```bash
git init
git add backend/requirements.txt backend/main.py
git commit -m "feat: initialize FastAPI backend"
```

---

## Task 2: 인증 — JWT 로그인

**Files:**
- Create: `backend/auth.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_auth.py`:
```python
import pytest
from fastapi.testclient import TestClient
import os
os.environ["SHARED_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

from main import app

client = TestClient(app)

def test_login_success():
    res = client.post("/auth/login", json={"password": "testpass"})
    assert res.status_code == 200
    assert "access_token" in res.cookies

def test_login_wrong_password():
    res = client.post("/auth/login", json={"password": "wrong"})
    assert res.status_code == 401

def test_protected_route_without_token():
    res = client.get("/settings")
    assert res.status_code == 401
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: FAIL (라우트 미존재)

- [ ] **Step 3: auth.py 구현**

```python
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Response, Cookie, HTTPException, Depends
from pydantic import BaseModel
from jose import jwt, JWTError

router = APIRouter()

SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
SHARED_PASSWORD = os.environ.get("SHARED_PASSWORD", "")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

class LoginRequest(BaseModel):
    password: str

def create_token() -> str:
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

def require_auth(access_token: str | None = Cookie(default=None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/auth/login")
def login(body: LoginRequest, response: Response):
    if body.password != SHARED_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong password")
    token = create_token()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=TOKEN_EXPIRE_HOURS * 3600,
        samesite="lax",
    )
    return {"ok": True}

@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}
```

- [ ] **Step 4: main.py에 라우터 등록 및 `/settings` 스텁 추가**

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router, require_auth

app = FastAPI(title="Doc Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/settings", dependencies=[Depends(require_auth)])
def get_settings_stub():
    return {"api_key_set": False}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_auth.py -v
```

Expected: 3 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/auth.py backend/main.py backend/tests/test_auth.py
git commit -m "feat: JWT login/logout authentication"
```

---

## Task 3: API 키 설정 관리

**Files:**
- Create: `backend/config.py`
- Create: `backend/tests/test_config.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_config.py`:
```python
import os, json, tempfile, pytest
os.environ["SHARED_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def _login():
    client.post("/auth/login", json={"password": "testpass"})

def test_get_settings_no_key(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_PATH", str(tmp_path / "config.json"))
    _login()
    res = client.get("/settings")
    assert res.status_code == 200
    assert res.json() == {"api_key_set": False}

def test_put_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_PATH", str(tmp_path / "config.json"))
    _login()
    res = client.put("/settings/api-key", json={"api_key": "AIza-test-key"})
    assert res.status_code == 200
    res2 = client.get("/settings")
    assert res2.json() == {"api_key_set": True}

def test_put_empty_key_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr("config.CONFIG_PATH", str(tmp_path / "config.json"))
    _login()
    res = client.put("/settings/api-key", json={"api_key": ""})
    assert res.status_code == 400
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_config.py -v
```

Expected: FAIL

- [ ] **Step 3: config.py 구현**

```python
import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import require_auth

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

router = APIRouter()

def _read() -> dict:
    try:
        return json.loads(Path(CONFIG_PATH).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def _write(data: dict):
    Path(CONFIG_PATH).write_text(json.dumps(data, indent=2))

def get_api_key() -> str | None:
    return _read().get("google_api_key")

class ApiKeyRequest(BaseModel):
    api_key: str

@router.get("/settings", dependencies=[Depends(require_auth)])
def get_settings():
    return {"api_key_set": bool(get_api_key())}

@router.put("/settings/api-key", dependencies=[Depends(require_auth)])
def update_api_key(body: ApiKeyRequest):
    if not body.api_key.strip():
        raise HTTPException(status_code=400, detail="API key cannot be empty")
    data = _read()
    data["google_api_key"] = body.api_key.strip()
    _write(data)
    return {"ok": True}
```

- [ ] **Step 4: main.py에 config 라우터 등록 (기존 /settings 스텁 제거)**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from config import router as config_router

app = FastAPI(title="Doc Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(config_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_config.py tests/test_auth.py -v
```

Expected: all passed

- [ ] **Step 6: config.json을 .gitignore에 추가**

`backend/.gitignore`:
```
.venv/
__pycache__/
config.json
*.pyc
```

- [ ] **Step 7: 커밋**

```bash
git add backend/config.py backend/tests/test_config.py backend/main.py backend/.gitignore
git commit -m "feat: API key settings storage and endpoints"
```

---

## Task 4: Google Translate 래퍼

**Files:**
- Create: `backend/translate.py`
- Create: `backend/tests/test_translate.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_translate.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from translate import batch_translate, TranslateError

def test_batch_translate_returns_translated_texts():
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.translations = [
        MagicMock(translated_text="Hello"),
        MagicMock(translated_text="World"),
    ]
    mock_client.translate_text.return_value = mock_response

    with patch("translate._make_client", return_value=mock_client):
        result = batch_translate(["안녕", "세계"], target_lang="en", api_key="fake")

    assert result == ["Hello", "World"]

def test_batch_translate_empty_list():
    result = batch_translate([], target_lang="en", api_key="fake")
    assert result == []

def test_batch_translate_raises_on_api_error():
    mock_client = MagicMock()
    mock_client.translate_text.side_effect = Exception("API error")

    with patch("translate._make_client", return_value=mock_client):
        with pytest.raises(TranslateError):
            batch_translate(["텍스트"], target_lang="en", api_key="fake")
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_translate.py -v
```

Expected: FAIL

- [ ] **Step 3: translate.py 구현**

```python
from google.cloud import translate_v2 as gtranslate

BATCH_SIZE = 128

class TranslateError(Exception):
    pass

def _make_client(api_key: str):
    import google.auth.credentials
    from google.oauth2.credentials import Credentials
    # API 키 방식 클라이언트
    return gtranslate.Client(client_options={"api_key": api_key})

def batch_translate(
    texts: list[str],
    target_lang: str,
    api_key: str,
    source_lang: str | None = None,
) -> list[str]:
    if not texts:
        return []

    client = _make_client(api_key)
    results: list[str] = []

    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i : i + BATCH_SIZE]
        for attempt in range(2):
            try:
                kwargs = {"target_language": target_lang, "values": chunk}
                if source_lang:
                    kwargs["source_language"] = source_lang
                response = client.translate(**kwargs)
                results.extend(r["translatedText"] for r in response)
                break
            except Exception as e:
                if attempt == 1:
                    raise TranslateError(str(e)) from e

    return results
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_translate.py -v
```

Expected: 3 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/translate.py backend/tests/test_translate.py
git commit -m "feat: Google Translate API batch wrapper"
```

---

## Task 5: Word(.docx) 프로세서

**Files:**
- Create: `backend/processors/__init__.py`
- Create: `backend/processors/docx.py`
- Create: `backend/tests/test_processor_docx.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_processor_docx.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_processor_docx.py -v
```

Expected: FAIL

- [ ] **Step 3: processors/docx.py 구현**

```python
import io
import copy
from docx import Document
from docx.oxml.ns import qn

def _iter_runs(doc: Document):
    """Yield (run, location_key) for all runs in body and tables."""
    for i, para in enumerate(doc.paragraphs):
        for j, run in enumerate(para.runs):
            yield run, ("para", i, j)
    for ti, table in enumerate(doc.tables):
        for ri, row in enumerate(table.rows):
            for ci, cell in enumerate(row.cells):
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
```

- [ ] **Step 4: `processors/__init__.py` 생성**

```python
# processors package
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_processor_docx.py -v
```

Expected: 3 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/processors/ backend/tests/test_processor_docx.py
git commit -m "feat: Word .docx text extraction and reinsert processor"
```

---

## Task 6: Excel(.xlsx) 프로세서

**Files:**
- Create: `backend/processors/xlsx.py`
- Create: `backend/tests/test_processor_xlsx.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_processor_xlsx.py`:
```python
import io
import openpyxl
from processors.xlsx import extract_texts, reinsert_texts

def _make_xlsx(cells: list) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for row_idx, row in enumerate(cells, 1):
        for col_idx, val in enumerate(row, 1):
            ws.cell(row=row_idx, column=col_idx, value=val)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()

def test_extract_text_cells_only():
    data = _make_xlsx([["안녕", 123, "=A1+1", None, "테스트"]])
    segments = extract_texts(data)
    texts = [s["text"] for s in segments]
    assert "안녕" in texts
    assert "테스트" in texts
    assert 123 not in texts
    assert "=A1+1" not in texts

def test_reinsert_preserves_non_text():
    data = _make_xlsx([[42, "안녕"]])
    segments = extract_texts(data)
    result = reinsert_texts(data, segments, ["Hello"])
    wb = openpyxl.load_workbook(io.BytesIO(result))
    ws = wb.active
    assert ws.cell(1, 1).value == 42
    assert ws.cell(1, 2).value == "Hello"
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_processor_xlsx.py -v
```

Expected: FAIL

- [ ] **Step 3: processors/xlsx.py 구현**

```python
import io
import openpyxl

def extract_texts(file_bytes: bytes) -> list[dict]:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    segments = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                if (
                    isinstance(cell.value, str)
                    and cell.value.strip()
                    and not cell.value.startswith("=")
                ):
                    segments.append({
                        "text": cell.value,
                        "key": (sheet_name, cell.row, cell.column),
                    })
    return segments

def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes))
    key_to_translation = {
        tuple(s["key"]): t for s, t in zip(segments, translated)
    }
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        for row in ws.iter_rows():
            for cell in row:
                key = (sheet_name, cell.row, cell.column)
                if key in key_to_translation:
                    cell.value = key_to_translation[key]
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_processor_xlsx.py -v
```

Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/processors/xlsx.py backend/tests/test_processor_xlsx.py
git commit -m "feat: Excel .xlsx text extraction and reinsert processor"
```

---

## Task 7: PowerPoint(.pptx) 프로세서

**Files:**
- Create: `backend/processors/pptx.py`
- Create: `backend/tests/test_processor_pptx.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_processor_pptx.py`:
```python
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
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_processor_pptx.py -v
```

Expected: FAIL

- [ ] **Step 3: processors/pptx.py 구현**

```python
import io
from pptx import Presentation

def extract_texts(file_bytes: bytes) -> list[dict]:
    prs = Presentation(io.BytesIO(file_bytes))
    segments = []
    for si, slide in enumerate(prs.slides):
        for shi, shape in enumerate(slide.shapes):
            if not shape.has_text_frame:
                continue
            for pi, para in enumerate(shape.text_frame.paragraphs):
                for ri, run in enumerate(para.runs):
                    if run.text.strip():
                        segments.append({
                            "text": run.text,
                            "key": (si, shi, pi, ri),
                        })
    return segments

def reinsert_texts(file_bytes: bytes, segments: list[dict], translated: list[str]) -> bytes:
    prs = Presentation(io.BytesIO(file_bytes))
    key_to_translation = {
        tuple(s["key"]): t for s, t in zip(segments, translated)
    }
    for si, slide in enumerate(prs.slides):
        for shi, shape in enumerate(slide.shapes):
            if not shape.has_text_frame:
                continue
            for pi, para in enumerate(shape.text_frame.paragraphs):
                for ri, run in enumerate(para.runs):
                    key = (si, shi, pi, ri)
                    if key in key_to_translation:
                        run.text = key_to_translation[key]
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_processor_pptx.py -v
```

Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/processors/pptx.py backend/tests/test_processor_pptx.py
git commit -m "feat: PowerPoint .pptx text extraction and reinsert processor"
```

---

## Task 8: 번역 엔드포인트 `POST /translate`

**Files:**
- Create: `backend/routers/translate_router.py`
- Create: `backend/routers/__init__.py`
- Create: `backend/tests/test_translate_endpoint.py`
- Modify: `backend/main.py`

- [ ] **Step 1: 실패 테스트 작성**

`backend/tests/test_translate_endpoint.py`:
```python
import io, os
os.environ["SHARED_PASSWORD"] = "testpass"
os.environ["SECRET_KEY"] = "testsecret"

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
from main import app

client = TestClient(app)

def _login():
    client.post("/auth/login", json={"password": "testpass"})

def _make_docx_bytes() -> bytes:
    from docx import Document
    doc = Document()
    doc.add_paragraph("안녕하세요")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()

def test_translate_docx():
    _login()
    with patch("config.get_api_key", return_value="fake-key"), \
         patch("translate.batch_translate", return_value=["Hello"]):
        res = client.post(
            "/translate",
            files={"file": ("test.docx", _make_docx_bytes(),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"target_lang": "en"},
        )
    assert res.status_code == 200
    assert res.headers["content-disposition"].endswith('.docx"')

def test_translate_no_api_key():
    _login()
    with patch("config.get_api_key", return_value=None):
        res = client.post(
            "/translate",
            files={"file": ("test.docx", _make_docx_bytes(),
                   "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            data={"target_lang": "en"},
        )
    assert res.status_code == 503

def test_translate_unsupported_format():
    _login()
    res = client.post(
        "/translate",
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"target_lang": "en"},
    )
    assert res.status_code == 400
```

- [ ] **Step 2: 테스트 실패 확인**

```bash
pytest tests/test_translate_endpoint.py -v
```

Expected: FAIL

- [ ] **Step 3: routers/translate_router.py 구현**

```python
import io
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from auth import require_auth
import config
import translate as tr
from processors import docx as docx_proc
from processors import xlsx as xlsx_proc
from processors import pptx as pptx_proc

router = APIRouter()

MAX_SIZE = 20 * 1024 * 1024  # 20MB

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
}

@router.post("/translate", dependencies=[Depends(require_auth)])
async def translate_file(
    file: UploadFile = File(...),
    target_lang: str = Form(...),
    source_lang: str | None = Form(default=None),
):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in PROCESSORS:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식: .{ext}")

    api_key = config.get_api_key()
    if not api_key:
        raise HTTPException(status_code=503, detail="API 키가 설정되지 않았습니다")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="파일이 20MB를 초과합니다")

    extract, reinsert, mime = PROCESSORS[ext]
    try:
        segments = extract(data)
    except Exception:
        raise HTTPException(status_code=422, detail="파일이 손상되었거나 읽을 수 없습니다")

    if segments:
        try:
            translated = tr.batch_translate(
                [s["text"] for s in segments],
                target_lang=target_lang,
                api_key=api_key,
                source_lang=source_lang or None,
            )
        except tr.TranslateError as e:
            raise HTTPException(status_code=502, detail=str(e))
    else:
        translated = []

    result = reinsert(data, segments, translated)

    stem = (file.filename or "file").rsplit(".", 1)[0]
    out_name = f"{stem}_{target_lang.upper()}.{ext}"

    return Response(
        content=result,
        media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{out_name}"'},
    )
```

- [ ] **Step 4: `routers/__init__.py` 생성**

```python
# routers package
```

- [ ] **Step 5: main.py에 라우터 등록**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from auth import router as auth_router
from config import router as config_router
from routers.translate_router import router as translate_router

app = FastAPI(title="Doc Translator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(translate_router)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 6: 전체 테스트 통과 확인**

```bash
pytest tests/ -v
```

Expected: all passed

- [ ] **Step 7: 커밋**

```bash
git add backend/routers/ backend/tests/test_translate_endpoint.py backend/main.py
git commit -m "feat: POST /translate endpoint with format routing"
```

---

## Task 9: 프론트엔드 초기화

**Files:**
- Create: `frontend/` (Vite + React + TypeScript)
- Create: `frontend/src/api.ts`

- [ ] **Step 1: Vite 프로젝트 생성**

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
```

- [ ] **Step 2: API 베이스 URL 프록시 설정**

`frontend/vite.config.ts`:
```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/translate': 'http://localhost:8000',
      '/settings': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
```

- [ ] **Step 3: api.ts 작성**

`frontend/src/api.ts`:
```ts
async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(path, { credentials: 'include', ...init })
  if (res.status === 401) {
    window.location.href = '/'
  }
  return res
}

export const api = {
  login: (password: string) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    }),

  logout: () => request('/auth/logout', { method: 'POST' }),

  getSettings: () => request('/settings'),

  updateApiKey: (api_key: string) =>
    request('/settings/api-key', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key }),
    }),

  translate: (file: File, targetLang: string, sourceLang?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('target_lang', targetLang)
    if (sourceLang) form.append('source_lang', sourceLang)
    return request('/translate', { method: 'POST', body: form })
  },
}
```

- [ ] **Step 4: 개발 서버 기동 확인**

```bash
cd frontend && npm run dev
```

브라우저에서 `http://localhost:5173` 접속 → Vite 기본 화면 확인

- [ ] **Step 5: 커밋**

```bash
git add frontend/
git commit -m "feat: initialize React frontend with Vite and API client"
```

---

## Task 10: 로그인 화면

**Files:**
- Create: `frontend/src/pages/Login.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Login.tsx 작성**

```tsx
import { useState } from 'react'
import { api } from '../api'

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const res = await api.login(password)
    setLoading(false)
    if (res.ok) {
      onSuccess()
    } else {
      setError('비밀번호가 틀렸습니다')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12, width: 300 }}>
        <h2 style={{ textAlign: 'center' }}>📄 Doc Translator</h2>
        <p style={{ textAlign: 'center', color: '#888', fontSize: 13 }}>팀 내부용 문서 번역 서비스</p>
        <input
          type="password"
          placeholder="비밀번호 입력..."
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}
        />
        {error && <p style={{ color: '#e03131', fontSize: 12, margin: 0 }}>{error}</p>}
        <button type="submit" disabled={loading || !password} style={{ padding: 10, borderRadius: 6, background: '#3b5bdb', color: '#fff', border: 'none', cursor: 'pointer' }}>
          {loading ? '확인 중...' : '입장하기'}
        </button>
      </form>
    </div>
  )
}
```

- [ ] **Step 2: App.tsx 작성 (라우팅)**

```tsx
import { useState, useEffect } from 'react'
import Login from './pages/Login'
import Translate from './pages/Translate'
import Settings from './pages/Settings'

type Page = 'login' | 'translate' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('login')

  if (page === 'login') return <Login onSuccess={() => setPage('translate')} />

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <span style={{ fontWeight: 'bold', fontSize: 18 }}>📄 Doc Translator</span>
        <div style={{ display: 'flex', gap: 16, fontSize: 14 }}>
          <button onClick={() => setPage('translate')} style={{ background: 'none', border: 'none', color: page === 'translate' ? '#74c0fc' : '#888', cursor: 'pointer' }}>번역</button>
          <button onClick={() => setPage('settings')} style={{ background: 'none', border: 'none', color: page === 'settings' ? '#74c0fc' : '#888', cursor: 'pointer' }}>설정</button>
        </div>
      </nav>
      {page === 'translate' && <Translate />}
      {page === 'settings' && <Settings />}
    </div>
  )
}
```

- [ ] **Step 3: 동작 확인**

백엔드(`uvicorn main:app --reload`)와 프론트엔드(`npm run dev`) 동시 실행 후:
1. `http://localhost:5173` → 로그인 화면 표시 확인
2. 잘못된 비밀번호 입력 → "비밀번호가 틀렸습니다" 표시 확인
3. 올바른 비밀번호 입력 → 번역 화면으로 이동 확인

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/
git commit -m "feat: login page and app routing"
```

---

## Task 11: 설정 화면 (API 키 관리)

**Files:**
- Create: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Settings.tsx 작성**

```tsx
import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Settings() {
  const [apiKeySet, setApiKeySet] = useState<boolean | null>(null)
  const [newKey, setNewKey] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSettings()
      .then(r => r.json())
      .then(d => setApiKeySet(d.api_key_set))
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaved(false)
    const res = await api.updateApiKey(newKey)
    if (res.ok) {
      setSaved(true)
      setApiKeySet(true)
      setNewKey('')
    } else {
      setError('저장에 실패했습니다')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2>설정</h2>
      <div style={{ padding: 16, border: '1px solid #333', borderRadius: 8 }}>
        <p style={{ margin: '0 0 8px', fontSize: 13, color: '#888' }}>Google Translate API 키</p>
        <p style={{ margin: '0 0 16px', fontWeight: 'bold', color: apiKeySet ? '#4caf50' : '#e03131' }}>
          {apiKeySet === null ? '확인 중...' : apiKeySet ? '✅ 설정됨' : '❌ 미설정'}
        </p>
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input
            type="password"
            placeholder="새 API 키 입력..."
            value={newKey}
            onChange={e => setNewKey(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}
          />
          {saved && <p style={{ color: '#4caf50', fontSize: 12, margin: 0 }}>✅ 저장됐습니다</p>}
          {error && <p style={{ color: '#e03131', fontSize: 12, margin: 0 }}>{error}</p>}
          <button type="submit" disabled={!newKey} style={{ padding: '8px 16px', borderRadius: 6, background: '#3b5bdb', color: '#fff', border: 'none', cursor: 'pointer', alignSelf: 'flex-start' }}>
            저장
          </button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: 동작 확인**

1. 설정 탭 클릭 → API 키 상태 표시 확인
2. 새 키 입력 후 저장 → "✅ 저장됐습니다" 표시 확인
3. 페이지 새로고침 후 "✅ 설정됨" 상태 유지 확인

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat: settings page for API key management"
```

---

## Task 12: 번역 메인 화면

**Files:**
- Create: `frontend/src/pages/Translate.tsx`

- [ ] **Step 1: Translate.tsx 작성**

```tsx
import { useState, useRef } from 'react'
import { api } from '../api'

const LANGUAGES = [
  { code: 'en', name: '영어' }, { code: 'ja', name: '일본어' },
  { code: 'zh', name: '중국어(간체)' }, { code: 'ko', name: '한국어' },
  { code: 'fr', name: '프랑스어' }, { code: 'de', name: '독일어' },
  { code: 'es', name: '스페인어' }, { code: 'vi', name: '베트남어' },
]

type State = 'idle' | 'translating' | 'done' | 'error'

export default function Translate() {
  const [file, setFile] = useState<File | null>(null)
  const [targetLang, setTargetLang] = useState('en')
  const [state, setState] = useState<State>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [downloadUrl, setDownloadUrl] = useState('')
  const [downloadName, setDownloadName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const handleTranslate = async () => {
    if (!file) return
    if (file.size > 20 * 1024 * 1024) {
      setErrorMsg('파일이 20MB를 초과합니다')
      return
    }
    setState('translating')
    setErrorMsg('')
    const res = await api.translate(file, targetLang)
    if (res.ok) {
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const disposition = res.headers.get('content-disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      setDownloadUrl(url)
      setDownloadName(match?.[1] ?? 'translated_file')
      setState('done')
    } else {
      const body = await res.json().catch(() => ({}))
      setErrorMsg(body.detail ?? '번역에 실패했습니다')
      setState('error')
    }
  }

  const reset = () => {
    setFile(null)
    setState('idle')
    setDownloadUrl('')
    setDownloadName('')
    setErrorMsg('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2>문서 번역</h2>

      {/* Upload zone */}
      <div
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        style={{ border: '2px dashed #3b5bdb', borderRadius: 12, padding: 40, textAlign: 'center', cursor: 'pointer', background: '#1a1a2e' }}
      >
        <input ref={inputRef} type="file" accept=".docx,.xlsx,.pptx" hidden onChange={e => setFile(e.target.files?.[0] ?? null)} />
        <p style={{ fontSize: 24 }}>📂</p>
        <p style={{ color: '#74c0fc', fontWeight: 'bold' }}>
          {file ? file.name : '파일을 드래그하거나 클릭해서 선택'}
        </p>
        <p style={{ color: '#888', fontSize: 12 }}>.docx · .xlsx · .pptx · 최대 20MB</p>
      </div>

      {/* Language select */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, color: '#888', display: 'block', marginBottom: 4 }}>번역할 언어</label>
          <select value={targetLang} onChange={e => setTargetLang(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}>
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
        </div>
      </div>

      {/* Action */}
      {state === 'idle' || state === 'error' ? (
        <>
          <button onClick={handleTranslate} disabled={!file}
            style={{ padding: 12, borderRadius: 8, background: file ? '#3b5bdb' : '#333', color: '#fff', border: 'none', cursor: file ? 'pointer' : 'not-allowed', fontSize: 15 }}>
            번역 시작
          </button>
          {errorMsg && <p style={{ color: '#e03131', fontSize: 13 }}>{errorMsg}</p>}
        </>
      ) : state === 'translating' ? (
        <div style={{ padding: 20, textAlign: 'center', color: '#74c0fc' }}>
          ⏳ 번역 중입니다. 잠시 기다려주세요...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <a href={downloadUrl} download={downloadName}
            style={{ display: 'block', padding: 12, borderRadius: 8, background: '#2f9e44', color: '#fff', textAlign: 'center', textDecoration: 'none', fontSize: 15 }}>
            ⬇️ {downloadName} 다운로드
          </a>
          <button onClick={reset} style={{ padding: 8, background: 'none', border: '1px solid #444', borderRadius: 6, color: '#888', cursor: 'pointer' }}>
            다른 파일 번역하기
          </button>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: 엔드투엔드 동작 확인**

1. 백엔드 실행: `cd backend && uvicorn main:app --reload`
2. 프론트엔드 실행: `cd frontend && npm run dev`
3. 로그인 → 설정에서 실제 Google API 키 저장
4. `.docx` 파일 업로드 → 영어 선택 → 번역 시작
5. 번역된 파일 다운로드 후 서식 보존 여부 확인

- [ ] **Step 3: 커밋**

```bash
git add frontend/src/pages/Translate.tsx
git commit -m "feat: translate main page with upload, progress and download"
```

---

## Task 13: Docker Compose 배포 설정

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml`
- Create: `.env.example`

- [ ] **Step 1: backend/Dockerfile 작성**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: frontend/nginx.conf 작성**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~ ^/(auth|translate|settings|health) {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
    }
}
```

- [ ] **Step 3: frontend/Dockerfile 작성**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

- [ ] **Step 4: docker-compose.yml 작성**

```yaml
services:
  backend:
    build: ./backend
    environment:
      - SHARED_PASSWORD=${SHARED_PASSWORD}
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - ./backend/config.json:/app/config.json
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped
```

- [ ] **Step 5: .env.example 작성**

```
SHARED_PASSWORD=your-team-password-here
SECRET_KEY=generate-a-random-secret-here
```

- [ ] **Step 6: 빌드 및 기동 확인**

```bash
cp .env.example .env
# .env 파일의 값을 실제 값으로 수정 후:
docker compose up --build
```

`http://localhost` 접속 → 로그인 화면 확인

- [ ] **Step 7: 커밋**

```bash
git add backend/Dockerfile frontend/Dockerfile frontend/nginx.conf docker-compose.yml .env.example
git add .gitignore  # .env 추가
git commit -m "feat: Docker Compose deployment configuration"
```

---

## Self-Review

**스펙 커버리지 체크:**

| 요구사항 | 구현 태스크 |
|---|---|
| .docx/.xlsx/.pptx 업로드 (20MB) | Task 8 (엔드포인트 검증) |
| Google Translate API 번역 | Task 4 (래퍼) + Task 8 |
| 서식 보존 | Task 5-7 (각 프로세서) |
| 동일 포맷 다운로드 | Task 8 |
| 원본 언어 자동 감지 | Task 4 (source_lang=None 시 API가 감지) |
| 팀 공유 비밀번호 | Task 2 |
| UI에서 API 키 교체 | Task 3 + Task 11 |
| 에러 처리 (400/401/413/422/502/503) | Task 8 |
| Docker 배포 | Task 13 |

**누락 없음. 모든 요구사항 커버됨.**
