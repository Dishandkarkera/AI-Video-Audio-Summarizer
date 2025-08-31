from fastapi import HTTPException, Depends, Header
from fastapi.security import OAuth2PasswordBearer
import jwt
from app.core.config import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")
settings = get_settings()

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
        return {"id": payload.get("sub")}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid auth token")


def get_current_user_optional(authorization: str | None = Header(None)):
    """Return user if a valid Bearer token is supplied, else anonymous.

    This is used for endpoints we want accessible without forcing auth (e.g. demo chat).
    """
    if not authorization:
        return {"id": "anon"}
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        token = parts[1]
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_alg])
            return {"id": payload.get("sub") or "anon"}
        except Exception:
            # Fall back to anonymous if invalid
            return {"id": "anon"}
    return {"id": "anon"}
