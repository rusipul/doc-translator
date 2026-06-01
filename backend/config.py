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
    p = Path(CONFIG_PATH)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)

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
