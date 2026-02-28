# Comprehensive Error Logging Guide

## Overview

The Kavalan backend implements comprehensive structured error logging that outputs JSON-formatted logs with full context including timestamps, component names, error types, stack traces, and request/session IDs.

This satisfies **Requirement 18.5**: "THE system SHALL log all errors with contextual information for debugging"

## Features

- **Structured JSON Output**: All logs are formatted as JSON for easy parsing and analysis
- **Full Context**: Includes timestamp, component, severity, error type, stack trace, and IDs
- **Multiple Severity Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Session/Request Tracking**: Automatically includes session_id, request_id, and user_id
- **Additional Context**: Support for arbitrary contextual key-value pairs
- **Stack Traces**: Automatic stack trace capture for exceptions

## Usage

### Basic Setup

```python
from app.utils.error_logger import get_error_logger

# Create a logger for your component
logger = get_error_logger("my_component")
```

### Logging Levels

#### INFO - Informational Messages
```python
logger.info(
    "Processing started",
    session_id=session_id,
    operation="transcribe"
)
```

#### WARNING - Warning Conditions
```python
try:
    risky_operation()
except Exception as e:
    logger.warning(
        "Operation failed, will retry",
        error=e,
        session_id=session_id,
        retry_count=2
    )
```

#### ERROR - Error Conditions
```python
try:
    critical_operation()
except Exception as e:
    logger.error(
        "Failed to process request",
        error=e,
        session_id=session_id,
        user_id=user_id,
        request_id=request_id,
        additional_data="context"
    )
```

#### CRITICAL - System-Level Failures
```python
try:
    database.connect()
except ConnectionError as e:
    logger.critical(
        "Database connection lost",
        error=e,
        database="postgresql",
        connection_pool_size=10
    )
```

### Convenience Method

```python
# Automatically logs with ERROR severity
try:
    process_data()
except Exception as e:
    logger.log_exception(
        e,
        session_id=session_id,
        input_size=1024
    )
```

## Log Output Format

All logs are output as JSON with the following structure:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "component": "audio_transcriber",
  "severity": "ERROR",
  "message": "Failed to transcribe audio",
  "error_type": "TranscriptionError",
  "error_message": "Audio format not supported",
  "stack_trace": [
    "Traceback (most recent call last):",
    "  File \"audio_transcriber.py\", line 42, in transcribe",
    "    result = whisper.transcribe(audio)",
    "TranscriptionError: Audio format not supported"
  ],
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "request_id": "req-12345",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "context": {
    "audio_duration": 5.2,
    "language": "hindi",
    "sample_rate": 16000
  }
}
```

## Integration Examples

### In Services

```python
from app.utils.error_logger import get_error_logger

class AudioTranscriber:
    def __init__(self):
        self.logger = get_error_logger("audio_transcriber")
    
    def transcribe(self, audio_data, session_id):
        try:
            self.logger.info(
                "Starting transcription",
                session_id=session_id,
                audio_size=len(audio_data)
            )
            
            result = self._process(audio_data)
            
            self.logger.info(
                "Transcription completed",
                session_id=session_id,
                transcript_length=len(result)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Transcription failed",
                error=e,
                session_id=session_id,
                audio_size=len(audio_data)
            )
            raise
```

### In API Routes

```python
from fastapi import APIRouter, HTTPException
from app.utils.error_logger import get_error_logger

router = APIRouter()
logger = get_error_logger("api_routes")

@router.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        logger.info(
            "Received analysis request",
            session_id=request.session_id,
            user_id=request.user_id
        )
        
        result = await process_analysis(request)
        return result
        
    except ValueError as e:
        logger.warning(
            "Invalid request data",
            error=e,
            session_id=request.session_id,
            request_data=request.dict()
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "Analysis failed",
            error=e,
            session_id=request.session_id,
            user_id=request.user_id
        )
        raise HTTPException(status_code=500, detail="Internal server error")
```

### In Celery Tasks

```python
from celery import Task
from app.celery_app import celery_app
from app.utils.error_logger import get_error_logger

logger = get_error_logger("celery_tasks")

@celery_app.task(bind=True, max_retries=3)
def analyze_audio_task(self, audio_data, session_id):
    try:
        logger.info(
            "Task started",
            session_id=session_id,
            task_id=self.request.id
        )
        
        result = process_audio(audio_data)
        
        logger.info(
            "Task completed",
            session_id=session_id,
            task_id=self.request.id
        )
        
        return result
        
    except Exception as e:
        logger.error(
            "Task failed",
            error=e,
            session_id=session_id,
            task_id=self.request.id,
            retry_count=self.request.retries
        )
        
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        else:
            logger.critical(
                "Task failed after max retries",
                error=e,
                session_id=session_id,
                task_id=self.request.id
            )
            raise
```

## Best Practices

1. **Always include session_id**: This helps trace requests across the system
2. **Include user_id for user actions**: Essential for debugging user-specific issues
3. **Add contextual information**: Include relevant data that helps debugging (sizes, counts, states)
4. **Use appropriate severity levels**: Don't log everything as ERROR
5. **Log exceptions with full context**: Always pass the exception object to capture stack traces
6. **Avoid logging sensitive data**: Don't log passwords, tokens, or PII in plain text

## Monitoring and Alerting

The structured JSON logs can be:
- Parsed by log aggregation tools (ELK, Splunk, CloudWatch)
- Filtered by severity level for alerting
- Searched by session_id or user_id for debugging
- Analyzed for error patterns and trends

## Performance Considerations

- Logging is synchronous and may add latency to critical paths
- Consider using async logging for high-throughput services
- Log at appropriate levels (avoid excessive DEBUG logging in production)
- Use sampling for high-frequency events

## Testing

The error logging module includes comprehensive unit tests:

```bash
pytest tests/test_error_logging.py -v
```

All tests verify:
- Correct JSON formatting
- Presence of all required fields
- Stack trace capture
- Context preservation
- Multiple severity levels
