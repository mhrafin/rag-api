from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader

from .config import get_settings

x_auth_token_header = APIKeyHeader(name="X-Auth-Token", auto_error=True)

settings = get_settings()


def verify_auth_secret(x_auth_token: str = Depends(x_auth_token_header)):
    if x_auth_token != settings.auth_secret:
        raise HTTPException(status_code=403, detail="Invalid X-Auth-Token header")
    return x_auth_token
