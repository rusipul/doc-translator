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
