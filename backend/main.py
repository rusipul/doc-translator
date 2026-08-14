from dotenv import load_dotenv, find_dotenv
# encoding='utf-8-sig' strips BOM written by PowerShell Set-Content -Encoding utf8
load_dotenv(find_dotenv(), encoding='utf-8-sig')

import os
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from auth import router as auth_router
from config import router as config_router
from routers.translate_router import router as translate_router

app = FastAPI(title="Doc Translator")

# ALLOWED_ORIGINS env var: comma-separated list of production frontend URLs
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"] + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# ALLOWED_IPS env var: comma-separated IPs. If not set, no restriction.
_allowed_ips = {ip.strip() for ip in os.environ.get("ALLOWED_IPS", "").split(",") if ip.strip()}

@app.middleware("http")
async def ip_whitelist(request: Request, call_next):
    if _allowed_ips and request.url.path != "/health":
        forwarded = request.headers.get("X-Forwarded-For", "")
        client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host or "")
        if client_ip not in _allowed_ips:
            return JSONResponse(status_code=403, content={"detail": "허가되지 않은 IP입니다"})
    return await call_next(request)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(tb)
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {exc}\n\n{tb}"},
    )

app.include_router(auth_router)
app.include_router(config_router)
app.include_router(translate_router)

@app.get("/health")
def health():
    return {"status": "ok"}
