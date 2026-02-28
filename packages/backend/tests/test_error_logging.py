"""
Unit Tests for Comprehensive Error Logging

Tests the structured error logging module to ensure all errors are logged
with proper context including timestamp, component, stack trace, and IDs.

Validates: Requirements 18.5
"""
import pytest
import json
import logging
from uuid import uuid4, UUID
from datetime import datetime
from app.utils.error_logger import (
    StructuredErrorLogger,
    ErrorSeverity,
    get_error_logger
)


class TestStructuredErrorLogger:
    """Test suite for StructuredErrorLogger"""
    
    def test_logger_initialization(self):
        """Test that logger initializes with correct component name"""
        logger = StructuredErrorLogger("test_component")
        assert logger.component == "test_component"
        assert logger.logger.name == "test_component"
    
    def test_format_log_entry_basic(self):
        """Test basic log entry formatting without error"""
        logger = StructuredErrorLogger("test_component")
        
        log_entry = logger._format_log_entry(
            ErrorSeverity.INFO,
            "Test message"
        )
        
        assert log_entry["component"] == "test_component"
        assert log_entry["severity"] == "INFO"
        assert log_entry["message"] == "Test message"
        assert "timestamp" in log_entry
        
        # Verify timestamp is ISO 8601 format
        timestamp = datetime.fromisoformat(log_entry["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)
    
    def test_format_log_entry_with_exception(self):
        """Test log entry formatting with exception and stack trace"""
        logger = StructuredErrorLogger("test_component")
        
        try:
            raise ValueError("Test error")
        except ValueError as e:
            log_entry = logger._format_log_entry(
                ErrorSeverity.ERROR,
                "An error occurred",
                error=e
            )
        
        assert log_entry["error_type"] == "ValueError"
        assert log_entry["error_message"] == "Test error"
        assert "stack_trace" in log_entry
        assert isinstance(log_entry["stack_trace"], list)
        assert len(log_entry["stack_trace"]) > 0
        assert "ValueError: Test error" in "".join(log_entry["stack_trace"])
    
    def test_format_log_entry_with_ids(self):
        """Test log entry formatting with session, request, and user IDs"""
        logger = StructuredErrorLogger("test_component")
        
        session_id = uuid4()
        user_id = uuid4()
        request_id = "req-12345"
        
        log_entry = logger._format_log_entry(
            ErrorSeverity.WARNING,
            "Warning message",
            session_id=session_id,
            request_id=request_id,
            user_id=user_id
        )
        
        assert log_entry["session_id"] == str(session_id)
        assert log_entry["request_id"] == request_id
        assert log_entry["user_id"] == str(user_id)
    
    def test_format_log_entry_with_additional_context(self):
        """Test log entry formatting with additional contextual information"""
        logger = StructuredErrorLogger("test_component")
        
        log_entry = logger._format_log_entry(
            ErrorSeverity.ERROR,
            "Processing failed",
            audio_duration=3.5,
            frame_count=30,
            platform="meet"
        )
        
        assert "context" in log_entry
        assert log_entry["context"]["audio_duration"] == 3.5
        assert log_entry["context"]["frame_count"] == 30
        assert log_entry["context"]["platform"] == "meet"
    
    def test_debug_logging(self, caplog):
        """Test debug-level logging"""
        caplog.set_level(logging.DEBUG)
        logger = StructuredErrorLogger("test_component")
        
        session_id = uuid4()
        logger.debug(
            "Debug message",
            session_id=session_id,
            detail="test detail"
        )
        
        # Parse the JSON log output
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["severity"] == "DEBUG"
        assert log_record["message"] == "Debug message"
        assert log_record["session_id"] == str(session_id)
        assert log_record["context"]["detail"] == "test detail"
    
    def test_info_logging(self, caplog):
        """Test info-level logging"""
        caplog.set_level(logging.INFO)
        logger = StructuredErrorLogger("test_component")
        
        logger.info("Info message", operation="transcribe")
        
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["severity"] == "INFO"
        assert log_record["message"] == "Info message"
        assert log_record["context"]["operation"] == "transcribe"
    
    def test_warning_logging(self, caplog):
        """Test warning-level logging with exception"""
        caplog.set_level(logging.WARNING)
        logger = StructuredErrorLogger("test_component")
        
        try:
            raise RuntimeError("Warning condition")
        except RuntimeError as e:
            logger.warning(
                "Warning occurred",
                error=e,
                retry_count=2
            )
        
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["severity"] == "WARNING"
        assert log_record["error_type"] == "RuntimeError"
        assert log_record["error_message"] == "Warning condition"
        assert "stack_trace" in log_record
    
    def test_error_logging(self, caplog):
        """Test error-level logging with full context"""
        caplog.set_level(logging.ERROR)
        logger = StructuredErrorLogger("audio_transcriber")
        
        session_id = uuid4()
        user_id = uuid4()
        
        try:
            raise Exception("Transcription failed")
        except Exception as e:
            logger.error(
                "Failed to transcribe audio",
                error=e,
                session_id=session_id,
                user_id=user_id,
                audio_duration=5.2,
                language="hindi"
            )
        
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["component"] == "audio_transcriber"
        assert log_record["severity"] == "ERROR"
        assert log_record["message"] == "Failed to transcribe audio"
        assert log_record["error_type"] == "Exception"
        assert log_record["error_message"] == "Transcription failed"
        assert log_record["session_id"] == str(session_id)
        assert log_record["user_id"] == str(user_id)
        assert log_record["context"]["audio_duration"] == 5.2
        assert log_record["context"]["language"] == "hindi"
        assert "stack_trace" in log_record
    
    def test_critical_logging(self, caplog):
        """Test critical-level logging"""
        caplog.set_level(logging.CRITICAL)
        logger = StructuredErrorLogger("database")
        
        try:
            raise ConnectionError("Database connection lost")
        except ConnectionError as e:
            logger.critical(
                "Critical database failure",
                error=e,
                database="postgresql",
                connection_pool_size=10
            )
        
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["severity"] == "CRITICAL"
        assert log_record["error_type"] == "ConnectionError"
        assert log_record["error_message"] == "Database connection lost"
    
    def test_log_exception_convenience_method(self, caplog):
        """Test log_exception convenience method"""
        caplog.set_level(logging.ERROR)
        logger = StructuredErrorLogger("test_component")
        
        session_id = uuid4()
        
        try:
            raise ValueError("Invalid input")
        except ValueError as e:
            logger.log_exception(
                e,
                session_id=session_id,
                input_value="invalid"
            )
        
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["severity"] == "ERROR"
        assert "Exception occurred: ValueError" in log_record["message"]
        assert log_record["error_type"] == "ValueError"
        assert log_record["session_id"] == str(session_id)
    
    def test_log_exception_with_custom_message(self, caplog):
        """Test log_exception with custom message"""
        caplog.set_level(logging.ERROR)
        logger = StructuredErrorLogger("test_component")
        
        try:
            raise KeyError("missing_key")
        except KeyError as e:
            logger.log_exception(
                e,
                message="Configuration key not found",
                config_file="settings.json"
            )
        
        log_record = json.loads(caplog.records[0].getMessage())
        assert log_record["message"] == "Configuration key not found"
        assert log_record["error_type"] == "KeyError"
    
    def test_get_error_logger_factory(self):
        """Test the factory function for creating error loggers"""
        logger = get_error_logger("my_component")
        
        assert isinstance(logger, StructuredErrorLogger)
        assert logger.component == "my_component"
    
    def test_json_output_is_valid(self, caplog):
        """Test that all log output is valid JSON"""
        caplog.set_level(logging.INFO)
        logger = StructuredErrorLogger("test_component")
        
        # Log various types of messages
        logger.info("Simple message")
        logger.warning("Warning", retry=True)
        
        try:
            raise Exception("Test error")
        except Exception as e:
            logger.error("Error occurred", error=e)
        
        # Verify all log records are valid JSON
        for record in caplog.records:
            log_data = json.loads(record.getMessage())
            assert isinstance(log_data, dict)
            assert "timestamp" in log_data
            assert "component" in log_data
            assert "severity" in log_data
            assert "message" in log_data
    
    def test_timestamp_format(self, caplog):
        """Test that timestamps are in ISO 8601 format with UTC timezone"""
        caplog.set_level(logging.INFO)
        logger = StructuredErrorLogger("test_component")
        
        logger.info("Test message")
        
        log_record = json.loads(caplog.records[0].getMessage())
        timestamp_str = log_record["timestamp"]
        
        # Should end with 'Z' for UTC
        assert timestamp_str.endswith("Z")
        
        # Should be parseable as ISO 8601
        timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)
    
    def test_stack_trace_includes_line_numbers(self, caplog):
        """Test that stack traces include file names and line numbers"""
        caplog.set_level(logging.ERROR)
        logger = StructuredErrorLogger("test_component")
        
        try:
            # This will be line X in the stack trace
            raise RuntimeError("Test error with stack trace")
        except RuntimeError as e:
            logger.error("Error with trace", error=e)
        
        log_record = json.loads(caplog.records[0].getMessage())
        stack_trace = "".join(log_record["stack_trace"])
        
        # Stack trace should include file name
        assert "test_error_logging.py" in stack_trace
        # Stack trace should include line numbers
        assert "line" in stack_trace.lower()
        # Stack trace should include the error message
        assert "Test error with stack trace" in stack_trace
    
    def test_multiple_context_fields(self, caplog):
        """Test logging with many contextual fields"""
        caplog.set_level(logging.ERROR)
        logger = StructuredErrorLogger("visual_analyzer")
        
        session_id = uuid4()
        user_id = uuid4()
        
        logger.error(
            "Frame analysis failed",
            session_id=session_id,
            user_id=user_id,
            request_id="req-abc-123",
            frame_number=42,
            frame_width=1920,
            frame_height=1080,
            platform="zoom",
            api_endpoint="gemini",
            retry_count=3,
            elapsed_time=2.5
        )
        
        log_record = json.loads(caplog.records[0].getMessage())
        
        # Verify all IDs are present
        assert log_record["session_id"] == str(session_id)
        assert log_record["user_id"] == str(user_id)
        assert log_record["request_id"] == "req-abc-123"
        
        # Verify all context fields are present
        context = log_record["context"]
        assert context["frame_number"] == 42
        assert context["frame_width"] == 1920
        assert context["frame_height"] == 1080
        assert context["platform"] == "zoom"
        assert context["api_endpoint"] == "gemini"
        assert context["retry_count"] == 3
        assert context["elapsed_time"] == 2.5


class TestErrorLoggingIntegration:
    """Integration tests for error logging across components"""
    
    def test_different_components_have_separate_loggers(self, caplog):
        """Test that different components can log independently"""
        caplog.set_level(logging.INFO)
        
        audio_logger = get_error_logger("audio_transcriber")
        visual_logger = get_error_logger("visual_analyzer")
        
        audio_logger.info("Audio processing started")
        visual_logger.info("Visual analysis started")
        
        assert len(caplog.records) == 2
        
        audio_log = json.loads(caplog.records[0].getMessage())
        visual_log = json.loads(caplog.records[1].getMessage())
        
        assert audio_log["component"] == "audio_transcriber"
        assert visual_log["component"] == "visual_analyzer"
    
    def test_nested_exception_logging(self, caplog):
        """Test logging of nested exceptions with full context"""
        caplog.set_level(logging.ERROR)
        logger = get_error_logger("test_component")
        
        try:
            try:
                raise ValueError("Inner error")
            except ValueError as inner:
                raise RuntimeError("Outer error") from inner
        except RuntimeError as e:
            logger.error("Nested exception occurred", error=e)
        
        log_record = json.loads(caplog.records[0].getMessage())
        stack_trace = "".join(log_record["stack_trace"])
        
        # Should contain both exceptions
        assert "RuntimeError: Outer error" in stack_trace
        assert "ValueError: Inner error" in stack_trace
