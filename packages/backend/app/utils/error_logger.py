"""
Comprehensive Error Logging Module

Provides structured JSON logging for all errors with context including:
- Timestamp
- Component name
- Error message and type
- Stack trace
- Request/Session IDs
- Additional contextual information

Validates: Requirements 18.5
"""
import logging
import json
import traceback
import sys
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from uuid import UUID
from enum import Enum


class ErrorSeverity(Enum):
    """Error severity levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class StructuredErrorLogger:
    """
    Structured error logger that outputs JSON-formatted logs with comprehensive context.
    
    All errors are logged with:
    - timestamp: ISO 8601 formatted timestamp
    - component: Name of the component/module where error occurred
    - severity: Error severity level
    - error_type: Type/class of the exception
    - error_message: Human-readable error message
    - stack_trace: Full stack trace for debugging
    - session_id: Session identifier (if available)
    - request_id: Request identifier (if available)
    - user_id: User identifier (if available)
    - additional_context: Any additional contextual information
    """
    
    def __init__(self, component: str):
        """
        Initialize structured error logger for a specific component.
        
        Args:
            component: Name of the component (e.g., 'audio_transcriber', 'visual_analyzer')
        """
        self.component = component
        self.logger = logging.getLogger(component)
    
    def _format_log_entry(
        self,
        severity: ErrorSeverity,
        message: str,
        error: Optional[Exception] = None,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **additional_context
    ) -> Dict[str, Any]:
        """
        Format a log entry as a structured JSON object.
        
        Args:
            severity: Error severity level
            message: Human-readable error message
            error: Exception object (if applicable)
            session_id: Session UUID
            request_id: Request identifier
            user_id: User UUID
            **additional_context: Additional contextual key-value pairs
        
        Returns:
            Dictionary containing structured log data
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "component": self.component,
            "severity": severity.value,
            "message": message,
        }
        
        # Add error details if exception provided
        if error:
            log_entry["error_type"] = type(error).__name__
            log_entry["error_message"] = str(error)
            log_entry["stack_trace"] = traceback.format_exception(
                type(error), error, error.__traceback__
            )
        
        # Add identifiers if provided
        if session_id:
            log_entry["session_id"] = str(session_id)
        if request_id:
            log_entry["request_id"] = request_id
        if user_id:
            log_entry["user_id"] = str(user_id)
        
        # Add any additional context
        if additional_context:
            log_entry["context"] = additional_context
        
        return log_entry
    
    def _log(self, log_entry: Dict[str, Any], severity: ErrorSeverity):
        """
        Output the log entry using the appropriate logging level.
        
        Args:
            log_entry: Structured log entry dictionary
            severity: Error severity level
        """
        json_log = json.dumps(log_entry, indent=None)
        
        if severity == ErrorSeverity.DEBUG:
            self.logger.debug(json_log)
        elif severity == ErrorSeverity.INFO:
            self.logger.info(json_log)
        elif severity == ErrorSeverity.WARNING:
            self.logger.warning(json_log)
        elif severity == ErrorSeverity.ERROR:
            self.logger.error(json_log)
        elif severity == ErrorSeverity.CRITICAL:
            self.logger.critical(json_log)
    
    def debug(
        self,
        message: str,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **context
    ):
        """Log debug-level message with context"""
        log_entry = self._format_log_entry(
            ErrorSeverity.DEBUG,
            message,
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            **context
        )
        self._log(log_entry, ErrorSeverity.DEBUG)
    
    def info(
        self,
        message: str,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **context
    ):
        """Log info-level message with context"""
        log_entry = self._format_log_entry(
            ErrorSeverity.INFO,
            message,
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            **context
        )
        self._log(log_entry, ErrorSeverity.INFO)
    
    def warning(
        self,
        message: str,
        error: Optional[Exception] = None,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **context
    ):
        """Log warning-level message with context"""
        log_entry = self._format_log_entry(
            ErrorSeverity.WARNING,
            message,
            error=error,
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            **context
        )
        self._log(log_entry, ErrorSeverity.WARNING)
    
    def error(
        self,
        message: str,
        error: Optional[Exception] = None,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **context
    ):
        """
        Log error-level message with full context and stack trace.
        
        Args:
            message: Human-readable error description
            error: Exception object
            session_id: Session UUID
            request_id: Request identifier
            user_id: User UUID
            **context: Additional contextual information
        """
        log_entry = self._format_log_entry(
            ErrorSeverity.ERROR,
            message,
            error=error,
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            **context
        )
        self._log(log_entry, ErrorSeverity.ERROR)
    
    def critical(
        self,
        message: str,
        error: Optional[Exception] = None,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **context
    ):
        """
        Log critical-level message with full context and stack trace.
        
        Critical errors indicate system-level failures that require immediate attention.
        
        Args:
            message: Human-readable error description
            error: Exception object
            session_id: Session UUID
            request_id: Request identifier
            user_id: User UUID
            **context: Additional contextual information
        """
        log_entry = self._format_log_entry(
            ErrorSeverity.CRITICAL,
            message,
            error=error,
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            **context
        )
        self._log(log_entry, ErrorSeverity.CRITICAL)
    
    def log_exception(
        self,
        error: Exception,
        message: Optional[str] = None,
        session_id: Optional[UUID] = None,
        request_id: Optional[str] = None,
        user_id: Optional[UUID] = None,
        **context
    ):
        """
        Log an exception with automatic severity determination.
        
        Convenience method that logs the exception with ERROR severity
        and includes full stack trace.
        
        Args:
            error: Exception object
            message: Optional custom message (defaults to exception message)
            session_id: Session UUID
            request_id: Request identifier
            user_id: User UUID
            **context: Additional contextual information
        """
        if message is None:
            message = f"Exception occurred: {type(error).__name__}"
        
        self.error(
            message,
            error=error,
            session_id=session_id,
            request_id=request_id,
            user_id=user_id,
            **context
        )


def get_error_logger(component: str) -> StructuredErrorLogger:
    """
    Factory function to create a structured error logger for a component.
    
    Args:
        component: Name of the component
    
    Returns:
        StructuredErrorLogger instance
    
    Example:
        >>> logger = get_error_logger("audio_transcriber")
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     logger.error(
        ...         "Failed to transcribe audio",
        ...         error=e,
        ...         session_id=session_id,
        ...         audio_duration=3.5
        ...     )
    """
    return StructuredErrorLogger(component)
