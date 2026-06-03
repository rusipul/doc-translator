from dotenv import load_dotenv, find_dotenv
# encoding='utf-8-sig' strips BOM written by PowerShell Set-Content -Encoding utf8
load_dotenv(find_dotenv(), encoding='utf-8-sig')

import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
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
