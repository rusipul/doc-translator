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
