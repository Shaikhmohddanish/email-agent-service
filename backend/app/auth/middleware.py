import os
import logging
from typing import Optional
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.db.supabase_client import supabase
from app.config import SUPABASE_URL, SUPABASE_JWT_SECRET

logger = logging.getLogger(__name__)
security = HTTPBearer()

# Supabase JWT secret is now imported from config.py


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify Supabase JWT and return user payload."""
    token = credentials.credentials
    try:
        # Let the Supabase Auth server verify the token and return the user securely
        user_res = supabase.auth.get_user(token)
        if not user_res or not user_res.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        
        # Build payload equivalent to what the app expects
        return {"sub": user_res.user.id, "email": user_res.user.email}

    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail=f"JWT Verification Error: {str(e)}")


async def get_current_user_id(payload: dict = Depends(verify_token)) -> str:
    """Extract user ID from verified JWT payload."""
    return payload["sub"]
