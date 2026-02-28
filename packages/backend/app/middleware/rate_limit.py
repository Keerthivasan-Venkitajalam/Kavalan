"""
Rate Limiting Middleware
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from redis import Redis
from app.config import settings
import time
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using Redis"""
    
    def __init__(self, app, redis_client: Redis):
        super().__init__(app)
        self.redis = redis_client
        self.rate_limit = settings.RATE_LIMIT_PER_MINUTE
        self.window = 60  # 60 seconds
    
    async def dispatch(self, request: Request, call_next):
        """Check rate limit before processing request"""
        # Skip rate limiting for health checks
        if request.url.path in ["/", "/health"]:
            return await call_next(request)
        
        # Get identifier (user_id from token or IP address)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        if not self._check_rate_limit(identifier):
            logger.warning(f"Rate limit exceeded for {identifier}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Maximum {self.rate_limit} requests per minute.",
                        "details": {
                            "retry_after": self.window,
                            "limit": self.rate_limit,
                            "remaining": 0
                        }
                    }
                }
            )
        
        response = await call_next(request)
        return response
    
    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        # Try to get user_id from authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from jose import jwt
                token = auth_header.split(" ")[1]
                payload = jwt.decode(
                    token,
                    settings.JWT_SECRET,
                    algorithms=[settings.JWT_ALGORITHM]
                )
                return f"user:{payload.get('user_id')}"
            except Exception:
                pass
        
        # Fall back to IP address
        client_ip = request.client.host
        return f"ip:{client_ip}"
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Check if request is within rate limit"""
        try:
            key = f"rate_limit:{identifier}"
            current_time = int(time.time())
            
            # Remove old entries outside the window
            self.redis.zremrangebyscore(key, 0, current_time - self.window)
            
            # Count requests in current window
            request_count = self.redis.zcard(key)
            
            if request_count >= self.rate_limit:
                return False
            
            # Add current request
            self.redis.zadd(key, {str(current_time): current_time})
            self.redis.expire(key, self.window)
            
            return True
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Allow request if Redis is unavailable
            return True
