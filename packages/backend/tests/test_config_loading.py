"""
Unit tests for configuration loading with multi-environment support
"""
import os
import pytest
from pathlib import Path
from unittest.mock import patch
from app.config import Settings, load_settings, get_config_file_path


class TestConfigurationLoading:
    """Test configuration loading from environment variables and config files"""
    
    def test_default_settings(self):
        """Test that default settings are loaded when no config files exist"""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()
            assert settings.ENVIRONMENT == "development"
            assert settings.DATABASE_URL == "postgresql://localhost:5432/kavalan"
            assert settings.JWT_ALGORITHM == "HS256"
    
    def test_environment_variable_override(self):
        """Test that environment variables override default settings"""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "DATABASE_URL": "postgresql://prod-db:5432/kavalan",
            "RATE_LIMIT_PER_MINUTE": "100",
            "JWT_SECRET": "a" * 32,  # Valid production secret
            "GEMINI_API_KEY": "test_key",
            "OPENAI_API_KEY": "test_key"
        }, clear=True):
            settings = Settings()
            assert settings.ENVIRONMENT == "production"
            assert settings.DATABASE_URL == "postgresql://prod-db:5432/kavalan"
            assert settings.RATE_LIMIT_PER_MINUTE == 100
    
    def test_environment_types(self):
        """Test that all supported environment types are valid"""
        valid_environments = ["development", "staging", "production", "test"]
        
        for env in valid_environments:
            env_vars = {"ENVIRONMENT": env}
            # Production requires additional valid settings
            if env == "production":
                env_vars.update({
                    "JWT_SECRET": "a" * 32,
                    "GEMINI_API_KEY": "test_key",
                    "OPENAI_API_KEY": "test_key"
                })
            
            with patch.dict(os.environ, env_vars, clear=True):
                settings = Settings()
                assert settings.ENVIRONMENT == env
    
    def test_cors_origins_list(self):
        """Test that CORS_ORIGINS is properly parsed as a list"""
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "https://example.com,https://test.com"
        }, clear=True):
            settings = Settings()
            # Pydantic should parse comma-separated string as list
            assert isinstance(settings.CORS_ORIGINS, list)
    
    def test_jwt_expiration_integer(self):
        """Test that JWT_EXPIRATION_MINUTES is parsed as integer"""
        with patch.dict(os.environ, {
            "JWT_EXPIRATION_MINUTES": "120"
        }, clear=True):
            settings = Settings()
            assert settings.JWT_EXPIRATION_MINUTES == 120
            assert isinstance(settings.JWT_EXPIRATION_MINUTES, int)
    
    def test_get_config_file_path_default(self):
        """Test getting config file path for default environment"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            path = get_config_file_path()
            assert path.name == ".env.development"
            assert path.parent.name == "backend"
    
    def test_get_config_file_path_specific_environment(self):
        """Test getting config file path for specific environment"""
        path = get_config_file_path("production")
        assert path.name == ".env.production"
        
        path = get_config_file_path("staging")
        assert path.name == ".env.staging"
        
        path = get_config_file_path("test")
        assert path.name == ".env.test"
    
    def test_load_settings_with_environment_variable(self):
        """Test that load_settings respects ENVIRONMENT variable"""
        with patch.dict(os.environ, {"ENVIRONMENT": "test"}, clear=True):
            settings = load_settings()
            # Should load .env.test if it exists
            assert settings.ENVIRONMENT == "test"
    
    def test_settings_case_sensitivity(self):
        """Test that settings are case-sensitive"""
        with patch.dict(os.environ, {
            "environment": "production",  # lowercase
            "ENVIRONMENT": "development"  # uppercase
        }, clear=True):
            settings = Settings()
            # Should use uppercase version
            assert settings.ENVIRONMENT == "development"
    
    def test_extra_fields_ignored(self):
        """Test that extra fields in environment are ignored"""
        with patch.dict(os.environ, {
            "UNKNOWN_FIELD": "some_value",
            "ANOTHER_UNKNOWN": "another_value"
        }, clear=True):
            # Should not raise an error
            settings = Settings()
            assert not hasattr(settings, "UNKNOWN_FIELD")
            assert not hasattr(settings, "ANOTHER_UNKNOWN")


class TestEnvironmentSpecificConfigs:
    """Test environment-specific configuration files"""
    
    def test_development_config_exists(self):
        """Test that development config file exists"""
        path = get_config_file_path("development")
        assert path.exists(), f"Development config file should exist at {path}"
    
    def test_staging_config_exists(self):
        """Test that staging config file exists"""
        path = get_config_file_path("staging")
        assert path.exists(), f"Staging config file should exist at {path}"
    
    def test_production_config_exists(self):
        """Test that production config file exists"""
        path = get_config_file_path("production")
        assert path.exists(), f"Production config file should exist at {path}"
    
    def test_test_config_exists(self):
        """Test that test config file exists"""
        path = get_config_file_path("test")
        assert path.exists(), f"Test config file should exist at {path}"


class TestConfigurationSecurity:
    """Test security-related configuration aspects"""
    
    def test_production_jwt_secret_not_default(self):
        """Test that production should not use default JWT secret"""
        # This test now validates that production enforces strong secrets
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "JWT_SECRET": "a" * 32,  # Valid production secret
            "GEMINI_API_KEY": "test_key",
            "OPENAI_API_KEY": "test_key"
        }, clear=True):
            settings = Settings()
            # In production, JWT_SECRET should be overridden via env var or config file
            # This test documents the expectation
            assert settings.JWT_SECRET is not None
            assert len(settings.JWT_SECRET) > 0
            assert settings.JWT_SECRET != "dev_secret_key_change_in_production"
    
    def test_api_keys_can_be_empty_in_dev(self):
        """Test that API keys can be empty in development"""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
            settings = Settings()
            # Empty API keys are acceptable in development
            assert isinstance(settings.GEMINI_API_KEY, str)
            assert isinstance(settings.OPENAI_API_KEY, str)
    
    def test_cors_origins_configurable(self):
        """Test that CORS origins are configurable"""
        with patch.dict(os.environ, {
            "CORS_ORIGINS": "https://secure-origin.com"
        }, clear=True):
            settings = Settings()
            assert isinstance(settings.CORS_ORIGINS, list)


class TestDatabaseConfiguration:
    """Test database-related configuration"""
    
    def test_database_urls_format(self):
        """Test that database URLs have correct format"""
        settings = Settings()
        
        # PostgreSQL URL should start with postgresql://
        assert settings.DATABASE_URL.startswith("postgresql://")
        
        # MongoDB URL should start with mongodb://
        assert settings.MONGODB_URL.startswith("mongodb://")
        
        # Redis URL should start with redis://
        assert settings.REDIS_URL.startswith("redis://")
    
    def test_celery_urls_match_redis(self):
        """Test that Celery URLs use Redis"""
        settings = Settings()
        
        assert settings.CELERY_BROKER_URL.startswith("redis://")
        assert settings.CELERY_RESULT_BACKEND.startswith("redis://")
    
    def test_database_urls_can_be_overridden(self):
        """Test that database URLs can be overridden via environment"""
        custom_db_url = "postgresql://custom-host:5432/custom-db"
        custom_mongo_url = "mongodb://custom-mongo:27017/custom-db"
        
        with patch.dict(os.environ, {
            "DATABASE_URL": custom_db_url,
            "MONGODB_URL": custom_mongo_url
        }, clear=True):
            settings = Settings()
            assert settings.DATABASE_URL == custom_db_url
            assert settings.MONGODB_URL == custom_mongo_url


class TestRateLimitConfiguration:
    """Test rate limiting configuration"""
    
    def test_rate_limit_default(self):
        """Test default rate limit value"""
        settings = Settings()
        assert settings.RATE_LIMIT_PER_MINUTE == 60
        assert isinstance(settings.RATE_LIMIT_PER_MINUTE, int)
    
    def test_rate_limit_configurable(self):
        """Test that rate limit can be configured"""
        with patch.dict(os.environ, {
            "RATE_LIMIT_PER_MINUTE": "200"
        }, clear=True):
            settings = Settings()
            assert settings.RATE_LIMIT_PER_MINUTE == 200


class TestJWTConfiguration:
    """Test JWT-related configuration"""
    
    def test_jwt_algorithm_default(self):
        """Test default JWT algorithm"""
        settings = Settings()
        assert settings.JWT_ALGORITHM == "HS256"
    
    def test_jwt_expiration_default(self):
        """Test default JWT expiration"""
        settings = Settings()
        assert settings.JWT_EXPIRATION_MINUTES == 60
    
    def test_jwt_settings_configurable(self):
        """Test that JWT settings can be configured"""
        with patch.dict(os.environ, {
            "JWT_SECRET": "custom_secret",
            "JWT_ALGORITHM": "HS512",
            "JWT_EXPIRATION_MINUTES": "120"
        }, clear=True):
            settings = Settings()
            assert settings.JWT_SECRET == "custom_secret"
            assert settings.JWT_ALGORITHM == "HS512"
            assert settings.JWT_EXPIRATION_MINUTES == 120
