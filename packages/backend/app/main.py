"""
Kavalan Backend API - Main FastAPI Application
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from app.config import settings
from app.middleware import RateLimitMiddleware, MetricsMiddleware
from app.routes import analyze_router, sessions_router, websocket_router, metrics_router
import logging
import json
from app.utils.error_logger import get_error_logger
from app.utils.metrics import initialize_metrics
from app.utils.tracing import (
    initialize_tracing,
    instrument_fastapi,
    instrument_redis,
    instrument_requests
)

# Configure structured JSON logging
class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""
    def format(self, record):
        # If the message is already JSON (from StructuredErrorLogger), return as-is
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            # Otherwise, format as simple JSON
            log_obj = {
                "timestamp": self.formatTime(record, self.datefmt),
                "component": record.name,
                "severity": record.levelname,
                "message": record.getMessage(),
            }
            if record.exc_info:
                log_obj["exception"] = self.formatException(record.exc_info)
            return json.dumps(log_obj)

# Set up root logger with JSON formatting
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)

# Get structured error logger for main app
error_logger = get_error_logger("main")

app = FastAPI(
    title="Kavalan API",
    description="Real-time Digital Arrest scam detection backend",
    version="1.0.0"
)

# Initialize Redis client for rate limiting
redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# Metrics middleware (add after rate limiting to track all requests)
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(analyze_router)
app.include_router(sessions_router)
app.include_router(websocket_router)
app.include_router(metrics_router)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    error_logger.info("Starting Kavalan API...")
    
    # Initialize OpenTelemetry tracing
    otlp_endpoint = settings.OTLP_ENDPOINT if hasattr(settings, 'OTLP_ENDPOINT') else None
    enable_console = settings.ENVIRONMENT == "development"
    initialize_tracing(
        service_name="kavalan-backend",
        service_version="1.0.0",
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console
    )
    error_logger.info("OpenTelemetry tracing initialized")
    
    # Instrument FastAPI
    instrument_fastapi(app)
    
    # Instrument Redis
    instrument_redis()
    
    # Instrument requests library
    instrument_requests()
    
    # Initialize Prometheus metrics
    initialize_metrics()
    error_logger.info("Prometheus metrics initialized")
    
    try:
        # Test Redis connection
        redis_client.ping()
        error_logger.info("Redis connection established")
    except Exception as e:
        error_logger.critical(
            "Failed to connect to Redis",
            error=e,
            redis_url=settings.REDIS_URL
        )

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    error_logger.info("Shutting down Kavalan API...")
    redis_client.close()

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "kavalan-api",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    redis_status = "connected"
    try:
        redis_client.ping()
    except Exception:
        redis_status = "disconnected"
    
    return {
        "status": "healthy",
        "redis": redis_status
    }
