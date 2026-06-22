# PDF 번역 지원 설계

**날짜:** 2026-06-22
**범위:** 텍스트 기반 PDF 파일의 번역 지원 추가 (스캔본 제외)

---

## 목표

기존 docx / xlsx / pptx 번역 파이프라인과 동일한 방식으로 PDF 번역을 지원한다.
입력 PDF를 받아 텍스트를 추출·번역·재삽입한 뒤 PDF를 반환한다.

---

## 범위 제한

- **지원:** 텍스트 레이어가 있는 PDF (Word/PowerPoint 등에서 내보낸 파일)
- **미지원:** 스캔본(이미지 전용) PDF — 빈 세그먼트로 감지하여 422 에러 반환

---

## 파일 구성

| 파일 | 변경 내용 |
|------|-----------|
| `backend/processors/pdf.py` | 신규 — `extract_texts`, `reinsert_texts` 구현 |
| `backend/tests/test_processor_pdf.py` | 신규 — 단위 테스트 |
| `backend/requirements.txt` | `pymupdf` 추가 |
| `backend/routers/translate_router.py` | `PROCESSORS`에 `pdf` 엔트리 추가 |

---

## 데이터 흐름

### extract_texts(file_bytes) → list[dict]

1. `fitz.open(stream=file_bytes, filetype="pdf")`로 PDF 로드
2. 페이지 → 블록(type=0, 텍스트 블록만) → 라인 → 스팬 순서로 순회
3. `span["text"].strip()`이 비어있지 않은 스팬만 세그먼트로 수집
4. 각 세그먼트의 key: `(page_idx, block_idx, line_idx, span_idx)`
5. 순회 후 세그먼트가 0개이면 `ValueError` 발생 → 라우터가 422로 변환

### reinsert_texts(file_bytes, segments, translated) → bytes

1. 원본 `file_bytes`로 PDF 재로드
2. 동일한 순회로 각 스팬의 `bbox`(위치 좌표) 확인
3. key가 `key_to_translation`에 있는 스팬에 대해:
   - `page.add_redact_annot(bbox, fill=(1,1,1))` — 원본 텍스트를 흰 사각형으로 덮음
   - `page.apply_redactions()` — 페이지 단위로 일괄 적용
   - `page.insert_text(origin, translated_text, fontname="cjk", fontsize=span["size"])` — 번역 텍스트 삽입
4. `doc.save(buf)`로 바이트 반환

---

## 폰트

PyMuPDF 내장 CJK 폰트(`"cjk"`)를 사용한다.
한국어·중국어·일본어를 모두 포함하며 별도 설치가 필요 없다.
원본 스팬의 폰트 크기는 그대로 유지한다.

---

## 에러 처리

| 상황 | 처리 |
|------|------|
| 스캔본 PDF (텍스트 없음) | `extract_texts`에서 `ValueError` → 라우터 422: "파일이 손상되었거나 읽을 수 없습니다" |
| 손상된 PDF | `fitz.open()` 예외 → 라우터 422 동일 처리 |
| 번역 텍스트가 박스보다 긴 경우 | 텍스트가 bbox 밖으로 넘칠 수 있음 — 1단계에서는 허용 |

---

## 테스트 케이스

1. **정상 추출** — 텍스트 PDF에서 `extract_texts` 실행 시 세그먼트 목록 반환
2. **재삽입 확인** — `reinsert_texts` 후 번역 텍스트가 PDF에 존재하는지 확인
3. **스캔본 감지** — 텍스트 없는 PDF(이미지 블록만) → `ValueError` 또는 빈 세그먼트 반환

---

## 의존성

```
pymupdf>=1.24.0
```

Render 서버 환경에서 pip 설치만으로 동작하며 시스템 바이너리 추가 설치 불필요.
