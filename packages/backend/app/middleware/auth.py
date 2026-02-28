"""
JWT Authentication Middleware
"""
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


class JWTAuthMiddleware:
    """JWT authentication middleware for FastAPI"""
    
    def __init__(self):
        self.secret = settings.JWT_SECRET
        self.algorithm = settings.JWT_ALGORITHM
    
    async def verify_token(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """Verify JWT token and return payload"""
        try:
            token = credentials.credentials
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def create_token(self, user_id: str, session_id: str) -> str:
        """Create JWT token for user"""
        from datetime import datetime, timedelta
        
        payload = {
            "user_id": user_id,
            "session_id": session_id,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRATION_MINUTES),
            "iat": datetime.utcnow()
        }
        
        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token


jwt_auth = JWTAuthMiddleware()


async def get_current_user(credentials: HTTPAuthorizationCredentials = security) -> dict:
    """Dependency to get current authenticated user"""
    return await jwt_auth.verify_token(credentials)
