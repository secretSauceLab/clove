# app/auth.py
import hmac
from fastapi import Header, HTTPException
from .db import settings


def require_api_key(x_api_key: str = Header(None)):
    if not settings.api_key:
        raise HTTPException(status_code=500, detail="API_KEY is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")