# Doc Translator — Design Spec

**Date:** 2026-06-01  
**Status:** Approved

---

## Overview

Office 문서(Word, Excel, PowerPoint)를 업로드하면 원본 서식을 유지한 채 원하는 언어로 번역해주는 팀 내부용 웹 서비스.

---

## Requirements

### 기능 요구사항

- `.docx`, `.xlsx`, `.pptx` 파일 업로드 지원 (최대 20MB)
- Google Translate API를 사용해 번역
- 원본 파일의 서식(폰트, 색상, 크기, 정렬, 수식 등) 보존
- 번역된 파일을 동일 포맷으로 다운로드
- 원본 언어 자동 감지 (Google Translate API의 언어 감지 기능 사용), 번역 대상 언어 수동 선택
- 팀 공유 비밀번호로 접근 제어
- 설정 페이지에서 Google Translate API 키를 UI로 변경 가능 (서버 재시작 없이 즉시 적용)

### 비기능 요구사항

- 단일 파일 처리 (배치 없음)
- 팀 내부용 (불특정 다수 대상 아님)
- HWP 미지원 (범위 외)

---

## Architecture

```
브라우저 (React)
    ↕ HTTP REST + JWT 쿠키
FastAPI 서버 (Python)
    ├── python-docx   → Word 처리
    ├── openpyxl      → Excel 처리
    ├── python-pptx   → PowerPoint 처리
    └── Google Translate API
```

### 배포 구성

- Docker Compose: FastAPI 컨테이너 + React/Nginx 컨테이너
- 환경변수: `SHARED_PASSWORD`, `SECRET_KEY`, `GOOGLE_TRANSLATE_API_KEY`

---

## API Endpoints

### `POST /auth/login`

- Body: `{ "password": string }`
- 성공: JWT 쿠키 설정 (HttpOnly, 24시간 만료), `200 OK`
- 실패: `401 Unauthorized`

### `GET /settings`

- Auth: JWT 쿠키 필요
- 성공: `{ "api_key_set": boolean }` — 키 존재 여부만 반환 (키 값 자체는 노출하지 않음)

### `PUT /settings/api-key`

- Auth: JWT 쿠키 필요
- Body: `{ "api_key": string }`
- API 키를 서버의 `config.json`에 저장, 즉시 적용
- 성공: `200 OK`
- 실패: `400` (빈 값)

### `POST /translate`

- Auth: JWT 쿠키 필요
- Body: multipart/form-data — `file` (업로드 파일), `target_lang` (언어 코드, 예: `en`), `source_lang` (선택, 없으면 자동 감지)
- 성공: 번역된 파일 반환 (동일 MIME 타입), 파일명은 `{원본명}_{LANG}.{확장자}` (LANG은 대문자 언어 코드, 예: `report_EN.xlsx`, `slides_JA.pptx`)
- 실패: `400` (포맷 오류), `413` (크기 초과), `502` (Google API 오류)

---

## File Processing Pipeline

모든 포맷 공통 흐름:

```
파일 수신 → 텍스트 세그먼트 추출 → 배치 번역 → 원본에 재삽입 → 반환
```

### Word (.docx) — python-docx

- Document → Paragraph → Run 단위로 순회
- Run별 텍스트를 추출, 번역 후 동일 Run에 재삽입
- Bold, italic, font size, color 등 Run 스타일 보존
- 표(Table) 내 셀도 동일하게 처리

### Excel (.xlsx) — openpyxl

- 모든 시트 순회, 셀 단위 처리
- 텍스트 셀만 번역 (문자열 타입)
- 수식(`=`로 시작), 숫자, 날짜, 빈 셀은 스킵
- 셀 서식(배경색, 테두리, 정렬) 보존

### PowerPoint (.pptx) — python-pptx

- Presentation → Slide → Shape → TextFrame → Paragraph → Run 단위 순회
- Run별 텍스트 교체, 폰트·색상·크기 보존
- 도형 위치·크기는 변경하지 않음

### Google Translate API 배치 처리

- 파일에서 텍스트 세그먼트를 모두 수집
- 128개 단위로 묶어 API 호출 (할당량 최적화)
- API 호출 실패 시 1회 재시도, 재시도 후 실패 시 `502` 반환

---

## Authentication

- 비밀번호는 서버 환경변수 `SHARED_PASSWORD`에 저장
- 로그인 성공 시 JWT 발급: `SECRET_KEY`로 서명, 24시간 TTL, HttpOnly 쿠키
- 모든 `/translate`, `/settings` 요청은 JWT 쿠키 검증 후 처리

## API Key 관리

- Google Translate API 키는 서버 측 `config.json`에 저장 (환경변수 아님)
- 서버는 각 번역 요청 시 `config.json`에서 키를 읽어 사용 (재시작 불필요)
- `config.json`에 키가 없으면 번역 시도 시 `503` + "API 키가 설정되지 않았습니다" 반환
- 키 값은 API로 읽어올 수 없음 (`api_key_set: true/false` 여부만 노출)

---

## Frontend (React)

### 화면 구성

**1. 로그인 화면** (`/`)
- 비밀번호 입력 필드 + 입장 버튼
- 오류 시 "비밀번호가 틀렸습니다" 표시

**2. 번역 메인 화면** (`/translate`)
- 파일 드래그앤드롭 영역 (클릭 업로드 겸용)
- 지원 포맷 안내 (.docx, .xlsx, .pptx, 최대 20MB)
- 원본 언어 드롭다운 (기본: 자동 감지)
- 번역 대상 언어 드롭다운
- 번역 시작 버튼 (파일 선택 전 비활성)
- 로그아웃 링크

**3. 번역 진행 화면** (메인 화면 인라인)
- 진행률 바 + 처리된 세그먼트 수 표시
- 취소 불가 (진행 중 이탈 시 서버는 계속 처리)

**4. 설정 화면** (`/settings`)
- 현재 API 키 설정 여부 표시 ("설정됨" / "미설정")
- 새 API 키 입력 필드 + 저장 버튼
- 저장 즉시 서버에 반영, 페이지 새로고침 없이 "저장됨" 확인
- 상단 네비게이션에서 접근 가능

**5. 완료 화면** (메인 화면 인라인)
- 다운로드 버튼 (번역된 파일)
- "다른 파일 번역하기" 링크 → 메인으로 초기화

---

## Error Handling

| 상황 | 처리 |
|---|---|
| 파일 20MB 초과 | 업로드 전 클라이언트 검증, `413` 반환 |
| 지원하지 않는 포맷 | `400` + 명확한 오류 메시지 |
| 잘못된 JWT / 만료 | `401` → 로그인 화면으로 리다이렉트 |
| Google API 실패 | 1회 재시도, 재시도 실패 시 `502` + 오류 메시지 |
| 파일 파싱 오류 | `422` + "파일이 손상되었거나 읽을 수 없습니다" |

---

## Project Structure

```
chapter1/
├── backend/
│   ├── main.py               # FastAPI 앱, 라우터
│   ├── auth.py               # 로그인, JWT 발급/검증
│   ├── config.py             # config.json 읽기/쓰기 (API 키 관리)
│   ├── translate.py          # Google Translate API 래퍼
│   ├── processors/
│   │   ├── docx.py           # Word 처리
│   │   ├── xlsx.py           # Excel 처리
│   │   └── pptx.py           # PowerPoint 처리
│   ├── config.json           # API 키 저장 (gitignore 처리)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.tsx
│   │   │   ├── Translate.tsx
│   │   │   └── Settings.tsx
│   │   └── App.tsx
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

---

## Out of Scope

- HWP 파일 지원
- 배치(다중 파일) 처리
- 사용자별 계정 관리
- 번역 이력 저장
- 유료 요금제 / 사용량 제한
