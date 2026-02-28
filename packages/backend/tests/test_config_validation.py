"""
Unit tests for configuration validation
Tests that invalid config values are rejected with descriptive errors
"""
import os
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from app.config import Settings, load_settings


class TestDatabaseURLValidation:
    """Test database URL validation"""
    
    def test_empty_database_url_rejected(self):
        """Test that empty DATABASE_URL is rejected"""
        with patch.dict(os.environ, {"DATABASE_URL": ""}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "DATABASE_URL cannot be empty" in str(exc_info.value)
    
    def test_invalid_database_url_protocol_rejected(self):
        """Test that DATABASE_URL with wrong protocol is rejected"""
        with patch.dict(os.environ, {"DATABASE_URL": "mysql://localhost:3306/db"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must start with 'postgresql://'" in str(exc_info.value)
    
    def test_valid_database_url_accepted(self):
        """Test that valid DATABASE_URL is accepted"""
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql://localhost:5432/kavalan"}, clear=True):
            settings = Settings()
            assert settings.DATABASE_URL == "postgresql://localhost:5432/kavalan"
    
    def test_empty_mongodb_url_rejected(self):
        """Test that empty MONGODB_URL is rejected"""
        with patch.dict(os.environ, {"MONGODB_URL": ""}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "MONGODB_URL cannot be empty" in str(exc_info.value)
    
    def test_invalid_mongodb_url_protocol_rejected(self):
        """Test that MONGODB_URL with wrong protocol is rejected"""
        with patch.dict(os.environ, {"MONGODB_URL": "http://localhost:27017/db"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must start with 'mongodb://'" in str(exc_info.value)
    
    def test_valid_mongodb_url_accepted(self):
        """Test that valid MONGODB_URL is accepted"""
        with patch.dict(os.environ, {"MONGODB_URL": "mongodb://localhost:27017/kavalan"}, clear=True):
            settings = Settings()
            assert settings.MONGODB_URL == "mongodb://localhost:27017/kavalan"
    
    def test_valid_mongodb_srv_url_accepted(self):
        """Test that mongodb+srv:// URL is accepted"""
        with patch.dict(os.environ, {"MONGODB_URL": "mongodb+srv://cluster.mongodb.net/db"}, clear=True):
            settings = Settings()
            assert settings.MONGODB_URL == "mongodb+srv://cluster.mongodb.net/db"
    
    def test_empty_redis_url_rejected(self):
        """Test that empty REDIS_URL is rejected"""
        with patch.dict(os.environ, {"REDIS_URL": ""}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "REDIS_URL cannot be empty" in str(exc_info.value)
    
    def test_invalid_redis_url_protocol_rejected(self):
        """Test that REDIS_URL with wrong protocol is rejected"""
        with patch.dict(os.environ, {"REDIS_URL": "http://localhost:6379/0"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must start with 'redis://'" in str(exc_info.value)
    
    def test_valid_redis_url_accepted(self):
        """Test that valid REDIS_URL is accepted"""
        with patch.dict(os.environ, {"REDIS_URL": "redis://localhost:6379/0"}, clear=True):
            settings = Settings()
            assert settings.REDIS_URL == "redis://localhost:6379/0"
    
    def test_valid_rediss_url_accepted(self):
        """Test that rediss:// (TLS) URL is accepted"""
        with patch.dict(os.environ, {"REDIS_URL": "rediss://secure-redis:6379/0"}, clear=True):
            settings = Settings()
            assert settings.REDIS_URL == "rediss://secure-redis:6379/0"


class TestJWTValidation:
    """Test JWT configuration validation"""
    
    def test_empty_jwt_secret_rejected(self):
        """Test that empty JWT_SECRET is rejected"""
        with patch.dict(os.environ, {"JWT_SECRET": ""}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "JWT_SECRET cannot be empty" in str(exc_info.value)
    
    def test_default_jwt_secret_rejected_in_production(self):
        """Test that default JWT_SECRET is rejected in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "dev_secret_key_change_in_production",
            "GEMINI_API_KEY": "test_key",
            "OPENAI_API_KEY": "test_key"
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be changed from default value" in str(exc_info.value)
    
    def test_short_jwt_secret_rejected_in_production(self):
        """Test that short JWT_SECRET is rejected in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "short_secret",
            "GEMINI_API_KEY": "test_key",
            "OPENAI_API_KEY": "test_key"
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be at least 32 characters" in str(exc_info.value)
    
    def test_valid_jwt_secret_accepted_in_production(self):
        """Test that valid JWT_SECRET is accepted in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,  # 32 character secret
            "GEMINI_API_KEY": "test_key",
            "OPENAI_API_KEY": "test_key"
        }, clear=True):
            settings = Settings()
            assert settings.JWT_SECRET == "a" * 32
    
    def test_short_jwt_secret_accepted_in_development(self):
        """Test that short JWT_SECRET is accepted in development"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "JWT_SECRET": "short"
        }, clear=True):
            settings = Settings()
            assert settings.JWT_SECRET == "short"
    
    def test_invalid_jwt_algorithm_rejected(self):
        """Test that invalid JWT_ALGORITHM is rejected"""
        with patch.dict(os.environ, {"JWT_ALGORITHM": "INVALID"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be one of" in str(exc_info.value)
            assert "HS256" in str(exc_info.value)
    
    def test_valid_jwt_algorithms_accepted(self):
        """Test that all valid JWT algorithms are accepted"""
        valid_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        
        for algo in valid_algorithms:
            with patch.dict(os.environ, {"JWT_ALGORITHM": algo}, clear=True):
                settings = Settings()
                assert settings.JWT_ALGORITHM == algo
    
    def test_negative_jwt_expiration_rejected(self):
        """Test that negative JWT_EXPIRATION_MINUTES is rejected"""
        with patch.dict(os.environ, {"JWT_EXPIRATION_MINUTES": "-10"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be positive" in str(exc_info.value)
    
    def test_zero_jwt_expiration_rejected(self):
        """Test that zero JWT_EXPIRATION_MINUTES is rejected"""
        with patch.dict(os.environ, {"JWT_EXPIRATION_MINUTES": "0"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be positive" in str(exc_info.value)
    
    def test_excessive_jwt_expiration_rejected(self):
        """Test that excessive JWT_EXPIRATION_MINUTES is rejected"""
        with patch.dict(os.environ, {"JWT_EXPIRATION_MINUTES": "50000"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must not exceed 43200" in str(exc_info.value)
    
    def test_valid_jwt_expiration_accepted(self):
        """Test that valid JWT_EXPIRATION_MINUTES is accepted"""
        with patch.dict(os.environ, {"JWT_EXPIRATION_MINUTES": "120"}, clear=True):
            settings = Settings()
            assert settings.JWT_EXPIRATION_MINUTES == 120


class TestRateLimitValidation:
    """Test rate limit validation"""
    
    def test_negative_rate_limit_rejected(self):
        """Test that negative RATE_LIMIT_PER_MINUTE is rejected"""
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "-10"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be positive" in str(exc_info.value)
    
    def test_zero_rate_limit_rejected(self):
        """Test that zero RATE_LIMIT_PER_MINUTE is rejected"""
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "0"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must be positive" in str(exc_info.value)
    
    def test_excessive_rate_limit_rejected(self):
        """Test that excessive RATE_LIMIT_PER_MINUTE is rejected"""
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "20000"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must not exceed 10000" in str(exc_info.value)
    
    def test_valid_rate_limit_accepted(self):
        """Test that valid RATE_LIMIT_PER_MINUTE is accepted"""
        with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": "100"}, clear=True):
            settings = Settings()
            assert settings.RATE_LIMIT_PER_MINUTE == 100


class TestCeleryValidation:
    """Test Celery configuration validation"""
    
    def test_empty_celery_broker_url_rejected(self):
        """Test that empty CELERY_BROKER_URL is rejected"""
        with patch.dict(os.environ, {"CELERY_BROKER_URL": ""}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "CELERY_BROKER_URL cannot be empty" in str(exc_info.value)
    
    def test_invalid_celery_broker_url_protocol_rejected(self):
        """Test that CELERY_BROKER_URL with wrong protocol is rejected"""
        with patch.dict(os.environ, {"CELERY_BROKER_URL": "amqp://localhost:5672"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must start with 'redis://'" in str(exc_info.value)
    
    def test_valid_celery_broker_url_accepted(self):
        """Test that valid CELERY_BROKER_URL is accepted"""
        with patch.dict(os.environ, {"CELERY_BROKER_URL": "redis://localhost:6379/0"}, clear=True):
            settings = Settings()
            assert settings.CELERY_BROKER_URL == "redis://localhost:6379/0"
    
    def test_empty_celery_result_backend_rejected(self):
        """Test that empty CELERY_RESULT_BACKEND is rejected"""
        with patch.dict(os.environ, {"CELERY_RESULT_BACKEND": ""}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "CELERY_RESULT_BACKEND cannot be empty" in str(exc_info.value)
    
    def test_invalid_celery_result_backend_protocol_rejected(self):
        """Test that CELERY_RESULT_BACKEND with wrong protocol is rejected"""
        with patch.dict(os.environ, {"CELERY_RESULT_BACKEND": "amqp://localhost:5672"}, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "must start with 'redis://'" in str(exc_info.value)
    
    def test_valid_celery_result_backend_accepted(self):
        """Test that valid CELERY_RESULT_BACKEND is accepted"""
        with patch.dict(os.environ, {"CELERY_RESULT_BACKEND": "redis://localhost:6379/1"}, clear=True):
            settings = Settings()
            assert settings.CELERY_RESULT_BACKEND == "redis://localhost:6379/1"


class TestAPIKeyValidation:
    """Test API key validation"""
    
    def test_empty_gemini_api_key_rejected_in_production(self):
        """Test that empty GEMINI_API_KEY is rejected in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "GEMINI_API_KEY": "",
            "OPENAI_API_KEY": "test_key",
            "JWT_SECRET": "a" * 32
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "GEMINI_API_KEY must be set in production" in str(exc_info.value)
    
    def test_empty_openai_api_key_rejected_in_production(self):
        """Test that empty OPENAI_API_KEY is rejected in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "GEMINI_API_KEY": "test_key",
            "OPENAI_API_KEY": "",
            "JWT_SECRET": "a" * 32
        }, clear=True):
            with pytest.raises(ValidationError) as exc_info:
                Settings()
            assert "OPENAI_API_KEY must be set in production" in str(exc_info.value)
    
    def test_empty_api_keys_accepted_in_development(self):
        """Test that empty API keys are accepted in development"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "GEMINI_API_KEY": "",
            "OPENAI_API_KEY": ""
        }, clear=True):
            settings = Settings()
            assert settings.GEMINI_API_KEY == ""
            assert settings.OPENAI_API_KEY == ""
    
    def test_valid_api_keys_accepted_in_production(self):
        """Test that valid API keys are accepted in production"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "GEMINI_API_KEY": "valid_gemini_key",
            "OPENAI_API_KEY": "valid_openai_key",
            "JWT_SECRET": "a" * 32
        }, clear=True):
            settings = Settings()
            assert settings.GEMINI_API_KEY == "valid_gemini_key"
            assert settings.OPENAI_API_KEY == "valid_openai_key"


class TestLoadSettingsValidation:
    """Test that load_settings() properly validates and reports errors"""
    
    def test_load_settings_with_invalid_config_raises_descriptive_error(self):
        """Test that load_settings raises ValueError with descriptive message"""
        with patch.dict(os.environ, {
            "DATABASE_URL": "invalid://url",
            "JWT_EXPIRATION_MINUTES": "-10"
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                load_settings()
            
            error_msg = str(exc_info.value)
            assert "Configuration validation failed" in error_msg
            assert "DATABASE_URL" in error_msg
            assert "JWT_EXPIRATION_MINUTES" in error_msg
    
    def test_load_settings_with_valid_config_succeeds(self):
        """Test that load_settings succeeds with valid configuration"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "development",
            "DATABASE_URL": "postgresql://localhost:5432/test",
            "MONGODB_URL": "mongodb://localhost:27017/test",
            "REDIS_URL": "redis://localhost:6379/0"
        }, clear=True):
            settings = load_settings()
            assert settings.ENVIRONMENT == "development"
            assert settings.DATABASE_URL == "postgresql://localhost:5432/test"
    
    def test_load_settings_production_validation(self):
        """Test that load_settings enforces production requirements"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "short",  # Too short for production
            "GEMINI_API_KEY": "test",
            "OPENAI_API_KEY": "test"
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                load_settings()
            
            error_msg = str(exc_info.value)
            assert "Configuration validation failed" in error_msg
            assert "JWT_SECRET" in error_msg


class TestMultipleValidationErrors:
    """Test that multiple validation errors are reported together"""
    
    def test_multiple_errors_reported_together(self):
        """Test that all validation errors are reported in one message"""
        with patch.dict(os.environ, {
            "DATABASE_URL": "invalid://url",
            "MONGODB_URL": "http://wrong",
            "REDIS_URL": "wrong://protocol",
            "JWT_EXPIRATION_MINUTES": "-10",
            "RATE_LIMIT_PER_MINUTE": "0"
        }, clear=True):
            with pytest.raises(ValueError) as exc_info:
                load_settings()
            
            error_msg = str(exc_info.value)
            # All errors should be in the message
            assert "DATABASE_URL" in error_msg
            assert "MONGODB_URL" in error_msg
            assert "REDIS_URL" in error_msg
            assert "JWT_EXPIRATION_MINUTES" in error_msg
            assert "RATE_LIMIT_PER_MINUTE" in error_msg
