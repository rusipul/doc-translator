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

    # NOTE: file is fully buffered before size check. For production, enforce
    # the limit at the Nginx/reverse-proxy level (client_max_body_size 20m).
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
                source_lang=source_lang,
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
