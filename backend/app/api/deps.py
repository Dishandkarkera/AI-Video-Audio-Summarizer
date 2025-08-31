from fastapi import Depends, HTTPException, Header
from typing import Optional
from app.core.security import decode_token

async def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == 'bearer':
        payload = decode_token(parts[1])
        if payload:
            return payload['sub']
    raise HTTPException(status_code=401, detail="Invalid token")
