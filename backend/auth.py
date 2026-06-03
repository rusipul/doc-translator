import os
import warnings
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Response, Cookie, HTTPException
from pydantic import BaseModel
from jose import jwt, JWTError

router = APIRouter()

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

# True when deployed to production (set PRODUCTION=true on Render)
_IS_PRODUCTION = os.environ.get("PRODUCTION", "false").lower() == "true"

def _secret_key() -> str:
    key = os.environ.get("SECRET_KEY", "change-me-in-production")
    if key == "change-me-in-production":
        warnings.warn("SECRET_KEY is using the default insecure value. Set SECRET_KEY env var before deploying.", stacklevel=2)
    return key

def _shared_password() -> str:
    return os.environ.get("SHARED_PASSWORD", "")

class LoginRequest(BaseModel):
    password: str

def create_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode({"exp": expire}, _secret_key(), algorithm=ALGORITHM)

def require_auth(access_token: str | None = Cookie(default=None)) -> None:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        jwt.decode(access_token, _secret_key(), algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

@router.post("/auth/login")
def login(body: LoginRequest, response: Response):
    if body.password != _shared_password():
        raise HTTPException(status_code=401, detail="Wrong password")
    token = create_token()
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=TOKEN_EXPIRE_HOURS * 3600,
        # Cross-domain (Vercel frontend + Render backend) requires SameSite=None + Secure
        samesite="none" if _IS_PRODUCTION else "lax",
        secure=_IS_PRODUCTION,
    )
    return {"ok": True}

@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"ok": True}
