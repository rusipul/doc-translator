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
