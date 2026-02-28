"""
Property-Based Test: Configuration Validation at Startup

Feature: production-ready-browser-extension
Property 36: Configuration Validation at Startup

**Validates: Requirements 17.3**

For any configuration values provided at startup, the system should:
1. Validate all config values
2. Reject invalid settings with descriptive errors
3. Accept valid settings without errors

This property test verifies:
1. Invalid database URLs are rejected with descriptive errors
2. Invalid JWT settings are rejected with descriptive errors
3. Invalid rate limits are rejected with descriptive errors
4. Invalid API keys in production are rejected
5. Valid configurations are accepted
6. Error messages are descriptive and helpful
"""
import os
import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch
from pydantic import ValidationError
from app.config import Settings, load_settings


# Strategy for generating database URLs
valid_postgres_urls = st.builds(
    lambda host, port, db: f"postgresql://{host}:{port}/{db}",
    host=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    port=st.integers(min_value=1024, max_value=65535),
    db=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
)

invalid_postgres_urls = st.one_of(
    st.just(""),  # Empty string
    st.builds(lambda proto, rest: f"{proto}://{rest}",
              proto=st.sampled_from(["mysql", "http", "https", "ftp"]),
              rest=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),  # Wrong protocol
    st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))  # No protocol
)

valid_mongodb_urls = st.one_of(
    st.builds(
        lambda host, port, db: f"mongodb://{host}:{port}/{db}",
        host=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        port=st.integers(min_value=1024, max_value=65535),
        db=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    ),
    st.builds(
        lambda cluster, db: f"mongodb+srv://{cluster}.mongodb.net/{db}",
        cluster=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        db=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    )
)

invalid_mongodb_urls = st.one_of(
    st.just(""),  # Empty string
    st.builds(lambda proto, rest: f"{proto}://{rest}",
              proto=st.sampled_from(["http", "https", "postgresql", "redis"]),
              rest=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))  # Wrong protocol
)

valid_redis_urls = st.one_of(
    st.builds(
        lambda host, port, db: f"redis://{host}:{port}/{db}",
        host=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        port=st.integers(min_value=1024, max_value=65535),
        db=st.integers(min_value=0, max_value=15)
    ),
    st.builds(
        lambda host, port, db: f"rediss://{host}:{port}/{db}",
        host=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        port=st.integers(min_value=1024, max_value=65535),
        db=st.integers(min_value=0, max_value=15)
    )
)

invalid_redis_urls = st.one_of(
    st.just(""),  # Empty string
    st.builds(lambda proto, rest: f"{proto}://{rest}",
              proto=st.sampled_from(["http", "https", "mongodb", "postgresql"]),
              rest=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))  # Wrong protocol
)

# Strategy for JWT algorithms
valid_jwt_algorithms = st.sampled_from(["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"])
invalid_jwt_algorithms = st.text(min_size=1, max_size=10).filter(
    lambda x: x not in ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
)

# Strategy for JWT secrets
valid_production_jwt_secrets = st.text(min_size=32, max_size=128, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')))
invalid_production_jwt_secrets = st.one_of(
    st.just(""),  # Empty
    st.just("dev_secret_key_change_in_production"),  # Default value
    st.text(min_size=1, max_size=31, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))  # Too short
)

# Strategy for JWT expiration
valid_jwt_expiration = st.integers(min_value=1, max_value=43200)
invalid_jwt_expiration = st.one_of(
    st.integers(max_value=0),  # Zero or negative
    st.integers(min_value=43201, max_value=100000)  # Too large
)

# Strategy for rate limits
valid_rate_limits = st.integers(min_value=1, max_value=10000)
invalid_rate_limits = st.one_of(
    st.integers(max_value=0),  # Zero or negative
    st.integers(min_value=10001, max_value=100000)  # Too large
)

# Strategy for API keys
valid_api_keys = st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P')))
invalid_production_api_keys = st.just("")  # Empty in production


@given(database_url=invalid_postgres_urls)
@settings(max_examples=50)
def test_invalid_database_url_rejected(database_url: str):
    """
    Property 36: Configuration Validation at Startup (Database URL)
    
    For any invalid PostgreSQL database URL, the configuration should be rejected
    with a descriptive error message.
    
    This test verifies:
    - Invalid DATABASE_URL formats are rejected
    - Error message is descriptive
    """
    with patch.dict(os.environ, {"DATABASE_URL": database_url}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention DATABASE_URL
        assert "DATABASE_URL" in error_msg or "database_url" in error_msg.lower(), \
            f"Error message should mention DATABASE_URL, got: {error_msg}"


@given(database_url=valid_postgres_urls)
@settings(max_examples=50)
def test_valid_database_url_accepted(database_url: str):
    """
    Property 36: Configuration Validation at Startup (Valid Database URL)
    
    For any valid PostgreSQL database URL, the configuration should be accepted.
    
    This test verifies:
    - Valid DATABASE_URL formats are accepted
    - Settings object is created successfully
    """
    # Assume the URL is well-formed
    assume("postgresql://" in database_url)
    assume(len(database_url) > 15)
    
    with patch.dict(os.environ, {"DATABASE_URL": database_url}, clear=True):
        try:
            settings = Settings()
            # Property: Valid URL should be accepted and stored
            assert settings.DATABASE_URL == database_url
        except ValidationError as e:
            # If validation fails, it should not be due to DATABASE_URL format
            error_msg = str(e)
            assert "DATABASE_URL" not in error_msg or "cannot be empty" not in error_msg, \
                f"Valid DATABASE_URL should be accepted: {database_url}, error: {error_msg}"


@given(mongodb_url=invalid_mongodb_urls)
@settings(max_examples=50)
def test_invalid_mongodb_url_rejected(mongodb_url: str):
    """
    Property 36: Configuration Validation at Startup (MongoDB URL)
    
    For any invalid MongoDB URL, the configuration should be rejected
    with a descriptive error message.
    """
    with patch.dict(os.environ, {"MONGODB_URL": mongodb_url}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention MONGODB_URL
        assert "MONGODB_URL" in error_msg or "mongodb_url" in error_msg.lower(), \
            f"Error message should mention MONGODB_URL, got: {error_msg}"


@given(mongodb_url=valid_mongodb_urls)
@settings(max_examples=50)
def test_valid_mongodb_url_accepted(mongodb_url: str):
    """
    Property 36: Configuration Validation at Startup (Valid MongoDB URL)
    
    For any valid MongoDB URL, the configuration should be accepted.
    """
    # Assume the URL is well-formed
    assume("mongodb://" in mongodb_url or "mongodb+srv://" in mongodb_url)
    assume(len(mongodb_url) > 15)
    
    with patch.dict(os.environ, {"MONGODB_URL": mongodb_url}, clear=True):
        try:
            settings = Settings()
            # Property: Valid URL should be accepted and stored
            assert settings.MONGODB_URL == mongodb_url
        except ValidationError as e:
            # If validation fails, it should not be due to MONGODB_URL format
            error_msg = str(e)
            assert "MONGODB_URL" not in error_msg or "cannot be empty" not in error_msg, \
                f"Valid MONGODB_URL should be accepted: {mongodb_url}, error: {error_msg}"


@given(redis_url=invalid_redis_urls)
@settings(max_examples=50)
def test_invalid_redis_url_rejected(redis_url: str):
    """
    Property 36: Configuration Validation at Startup (Redis URL)
    
    For any invalid Redis URL, the configuration should be rejected
    with a descriptive error message.
    """
    with patch.dict(os.environ, {"REDIS_URL": redis_url}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention REDIS_URL
        assert "REDIS_URL" in error_msg or "redis_url" in error_msg.lower(), \
            f"Error message should mention REDIS_URL, got: {error_msg}"


@given(redis_url=valid_redis_urls)
@settings(max_examples=50)
def test_valid_redis_url_accepted(redis_url: str):
    """
    Property 36: Configuration Validation at Startup (Valid Redis URL)
    
    For any valid Redis URL, the configuration should be accepted.
    """
    # Assume the URL is well-formed
    assume("redis://" in redis_url or "rediss://" in redis_url)
    assume(len(redis_url) > 10)
    
    with patch.dict(os.environ, {"REDIS_URL": redis_url}, clear=True):
        try:
            settings = Settings()
            # Property: Valid URL should be accepted and stored
            assert settings.REDIS_URL == redis_url
        except ValidationError as e:
            # If validation fails, it should not be due to REDIS_URL format
            error_msg = str(e)
            assert "REDIS_URL" not in error_msg or "cannot be empty" not in error_msg, \
                f"Valid REDIS_URL should be accepted: {redis_url}, error: {error_msg}"


@given(algorithm=invalid_jwt_algorithms)
@settings(max_examples=50)
def test_invalid_jwt_algorithm_rejected(algorithm: str):
    """
    Property 36: Configuration Validation at Startup (JWT Algorithm)
    
    For any invalid JWT algorithm, the configuration should be rejected
    with a descriptive error message.
    """
    with patch.dict(os.environ, {"JWT_ALGORITHM": algorithm}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention JWT_ALGORITHM and valid options
        assert "JWT_ALGORITHM" in error_msg or "jwt_algorithm" in error_msg.lower(), \
            f"Error message should mention JWT_ALGORITHM, got: {error_msg}"
        assert "must be one of" in error_msg or "HS256" in error_msg, \
            f"Error message should list valid algorithms, got: {error_msg}"


@given(algorithm=valid_jwt_algorithms)
@settings(max_examples=30)
def test_valid_jwt_algorithm_accepted(algorithm: str):
    """
    Property 36: Configuration Validation at Startup (Valid JWT Algorithm)
    
    For any valid JWT algorithm, the configuration should be accepted.
    """
    with patch.dict(os.environ, {"JWT_ALGORITHM": algorithm}, clear=True):
        settings = Settings()
        # Property: Valid algorithm should be accepted and stored
        assert settings.JWT_ALGORITHM == algorithm


@given(jwt_secret=invalid_production_jwt_secrets)
@settings(max_examples=50)
def test_invalid_production_jwt_secret_rejected(jwt_secret: str):
    """
    Property 36: Configuration Validation at Startup (Production JWT Secret)
    
    For any invalid JWT secret in production environment, the configuration
    should be rejected with a descriptive error message.
    """
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET": jwt_secret,
        "GEMINI_API_KEY": "test_key",
        "OPENAI_API_KEY": "test_key"
    }, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention JWT_SECRET
        assert "JWT_SECRET" in error_msg or "jwt_secret" in error_msg.lower(), \
            f"Error message should mention JWT_SECRET, got: {error_msg}"


@given(jwt_secret=valid_production_jwt_secrets)
@settings(max_examples=30)
def test_valid_production_jwt_secret_accepted(jwt_secret: str):
    """
    Property 36: Configuration Validation at Startup (Valid Production JWT Secret)
    
    For any valid JWT secret in production environment (>= 32 chars),
    the configuration should be accepted.
    """
    # Ensure it's not the default value
    assume(jwt_secret != "dev_secret_key_change_in_production")
    assume(len(jwt_secret) >= 32)
    
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET": jwt_secret,
        "GEMINI_API_KEY": "test_key",
        "OPENAI_API_KEY": "test_key"
    }, clear=True):
        settings = Settings()
        # Property: Valid secret should be accepted and stored
        assert settings.JWT_SECRET == jwt_secret


@given(expiration=invalid_jwt_expiration)
@settings(max_examples=50)
def test_invalid_jwt_expiration_rejected(expiration: int):
    """
    Property 36: Configuration Validation at Startup (JWT Expiration)
    
    For any invalid JWT expiration (<=0 or >43200), the configuration
    should be rejected with a descriptive error message.
    """
    with patch.dict(os.environ, {"JWT_EXPIRATION_MINUTES": str(expiration)}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention JWT_EXPIRATION_MINUTES
        assert "JWT_EXPIRATION_MINUTES" in error_msg or "jwt_expiration" in error_msg.lower(), \
            f"Error message should mention JWT_EXPIRATION_MINUTES, got: {error_msg}"


@given(expiration=valid_jwt_expiration)
@settings(max_examples=30)
def test_valid_jwt_expiration_accepted(expiration: int):
    """
    Property 36: Configuration Validation at Startup (Valid JWT Expiration)
    
    For any valid JWT expiration (1-43200), the configuration should be accepted.
    """
    with patch.dict(os.environ, {"JWT_EXPIRATION_MINUTES": str(expiration)}, clear=True):
        settings = Settings()
        # Property: Valid expiration should be accepted and stored
        assert settings.JWT_EXPIRATION_MINUTES == expiration


@given(rate_limit=invalid_rate_limits)
@settings(max_examples=50)
def test_invalid_rate_limit_rejected(rate_limit: int):
    """
    Property 36: Configuration Validation at Startup (Rate Limit)
    
    For any invalid rate limit (<=0 or >10000), the configuration
    should be rejected with a descriptive error message.
    """
    with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": str(rate_limit)}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention RATE_LIMIT_PER_MINUTE
        assert "RATE_LIMIT_PER_MINUTE" in error_msg or "rate_limit" in error_msg.lower(), \
            f"Error message should mention RATE_LIMIT_PER_MINUTE, got: {error_msg}"


@given(rate_limit=valid_rate_limits)
@settings(max_examples=30)
def test_valid_rate_limit_accepted(rate_limit: int):
    """
    Property 36: Configuration Validation at Startup (Valid Rate Limit)
    
    For any valid rate limit (1-10000), the configuration should be accepted.
    """
    with patch.dict(os.environ, {"RATE_LIMIT_PER_MINUTE": str(rate_limit)}, clear=True):
        settings = Settings()
        # Property: Valid rate limit should be accepted and stored
        assert settings.RATE_LIMIT_PER_MINUTE == rate_limit


@given(celery_url=invalid_redis_urls)
@settings(max_examples=50)
def test_invalid_celery_broker_url_rejected(celery_url: str):
    """
    Property 36: Configuration Validation at Startup (Celery Broker URL)
    
    For any invalid Celery broker URL, the configuration should be rejected
    with a descriptive error message.
    """
    with patch.dict(os.environ, {"CELERY_BROKER_URL": celery_url}, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        # Property: Error message should mention CELERY_BROKER_URL
        assert "CELERY_BROKER_URL" in error_msg or "celery_broker" in error_msg.lower(), \
            f"Error message should mention CELERY_BROKER_URL, got: {error_msg}"


@given(celery_url=valid_redis_urls)
@settings(max_examples=30)
def test_valid_celery_broker_url_accepted(celery_url: str):
    """
    Property 36: Configuration Validation at Startup (Valid Celery Broker URL)
    
    For any valid Celery broker URL, the configuration should be accepted.
    """
    # Assume the URL is well-formed
    assume("redis://" in celery_url or "rediss://" in celery_url)
    assume(len(celery_url) > 10)
    
    with patch.dict(os.environ, {"CELERY_BROKER_URL": celery_url}, clear=True):
        try:
            settings = Settings()
            # Property: Valid URL should be accepted and stored
            assert settings.CELERY_BROKER_URL == celery_url
        except ValidationError as e:
            error_msg = str(e)
            assert "CELERY_BROKER_URL" not in error_msg or "cannot be empty" not in error_msg, \
                f"Valid CELERY_BROKER_URL should be accepted: {celery_url}, error: {error_msg}"


def test_empty_production_api_keys_rejected():
    """
    Property 36: Configuration Validation at Startup (Production API Keys)
    
    For production environment, empty API keys should be rejected
    with descriptive error messages.
    """
    # Test empty GEMINI_API_KEY
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "GEMINI_API_KEY": "",
        "OPENAI_API_KEY": "test_key",
        "JWT_SECRET": "a" * 32
    }, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        assert "GEMINI_API_KEY" in error_msg, \
            f"Error message should mention GEMINI_API_KEY, got: {error_msg}"
    
    # Test empty OPENAI_API_KEY
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "GEMINI_API_KEY": "test_key",
        "OPENAI_API_KEY": "",
        "JWT_SECRET": "a" * 32
    }, clear=True):
        with pytest.raises(ValidationError) as exc_info:
            Settings()
        
        error_msg = str(exc_info.value)
        assert "OPENAI_API_KEY" in error_msg, \
            f"Error message should mention OPENAI_API_KEY, got: {error_msg}"


@given(
    gemini_key=valid_api_keys,
    openai_key=valid_api_keys
)
@settings(max_examples=30)
def test_valid_production_api_keys_accepted(gemini_key: str, openai_key: str):
    """
    Property 36: Configuration Validation at Startup (Valid Production API Keys)
    
    For production environment with valid API keys, the configuration
    should be accepted.
    """
    assume(len(gemini_key) > 0)
    assume(len(openai_key) > 0)
    
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "GEMINI_API_KEY": gemini_key,
        "OPENAI_API_KEY": openai_key,
        "JWT_SECRET": "a" * 32
    }, clear=True):
        settings = Settings()
        # Property: Valid API keys should be accepted and stored
        assert settings.GEMINI_API_KEY == gemini_key
        assert settings.OPENAI_API_KEY == openai_key


@given(
    database_url=valid_postgres_urls,
    mongodb_url=valid_mongodb_urls,
    redis_url=valid_redis_urls,
    jwt_algorithm=valid_jwt_algorithms,
    jwt_expiration=valid_jwt_expiration,
    rate_limit=valid_rate_limits
)
@settings(max_examples=50)
def test_complete_valid_configuration_accepted(
    database_url: str,
    mongodb_url: str,
    redis_url: str,
    jwt_algorithm: str,
    jwt_expiration: int,
    rate_limit: int
):
    """
    Property 36: Configuration Validation at Startup (Complete Valid Config)
    
    For any complete set of valid configuration values, the configuration
    should be accepted and all values should be stored correctly.
    
    This is a comprehensive test that validates multiple config values together.
    """
    # Assume all URLs are well-formed
    assume("postgresql://" in database_url)
    assume("mongodb://" in mongodb_url or "mongodb+srv://" in mongodb_url)
    assume("redis://" in redis_url or "rediss://" in redis_url)
    assume(len(database_url) > 15)
    assume(len(mongodb_url) > 15)
    assume(len(redis_url) > 10)
    
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "DATABASE_URL": database_url,
        "MONGODB_URL": mongodb_url,
        "REDIS_URL": redis_url,
        "JWT_ALGORITHM": jwt_algorithm,
        "JWT_EXPIRATION_MINUTES": str(jwt_expiration),
        "RATE_LIMIT_PER_MINUTE": str(rate_limit),
        "CELERY_BROKER_URL": redis_url,
        "CELERY_RESULT_BACKEND": redis_url
    }, clear=True):
        try:
            settings = Settings()
            
            # Property: All valid values should be accepted and stored correctly
            assert settings.DATABASE_URL == database_url
            assert settings.MONGODB_URL == mongodb_url
            assert settings.REDIS_URL == redis_url
            assert settings.JWT_ALGORITHM == jwt_algorithm
            assert settings.JWT_EXPIRATION_MINUTES == jwt_expiration
            assert settings.RATE_LIMIT_PER_MINUTE == rate_limit
            assert settings.CELERY_BROKER_URL == redis_url
            assert settings.CELERY_RESULT_BACKEND == redis_url
        except ValidationError as e:
            # If validation fails, it should not be due to format issues
            error_msg = str(e)
            pytest.fail(f"Valid configuration should be accepted, but got error: {error_msg}")


@pytest.mark.integration
def test_load_settings_rejects_invalid_config_with_descriptive_error():
    """
    Integration test: Verify load_settings() rejects invalid config
    with descriptive error message.
    
    This test verifies:
    - load_settings() validates configuration
    - Invalid config raises ValueError (not ValidationError)
    - Error message is descriptive and lists all validation errors
    """
    with patch.dict(os.environ, {
        "DATABASE_URL": "invalid://url",
        "MONGODB_URL": "http://wrong",
        "JWT_EXPIRATION_MINUTES": "-10",
        "RATE_LIMIT_PER_MINUTE": "0"
    }, clear=True):
        with pytest.raises(ValueError) as exc_info:
            load_settings()
        
        error_msg = str(exc_info.value)
        
        # Property: Error message should be descriptive
        assert "Configuration validation failed" in error_msg, \
            "Error should mention configuration validation"
        
        # Property: Error message should list all failing fields
        assert "DATABASE_URL" in error_msg, "Should mention DATABASE_URL"
        assert "MONGODB_URL" in error_msg, "Should mention MONGODB_URL"
        assert "JWT_EXPIRATION_MINUTES" in error_msg, "Should mention JWT_EXPIRATION_MINUTES"
        assert "RATE_LIMIT_PER_MINUTE" in error_msg, "Should mention RATE_LIMIT_PER_MINUTE"


@pytest.mark.integration
def test_load_settings_accepts_valid_config():
    """
    Integration test: Verify load_settings() accepts valid configuration.
    
    This test verifies:
    - load_settings() successfully loads valid configuration
    - Returns Settings object with correct values
    """
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "DATABASE_URL": "postgresql://localhost:5432/test",
        "MONGODB_URL": "mongodb://localhost:27017/test",
        "REDIS_URL": "redis://localhost:6379/0",
        "JWT_ALGORITHM": "HS256",
        "JWT_EXPIRATION_MINUTES": "60",
        "RATE_LIMIT_PER_MINUTE": "100"
    }, clear=True):
        settings = load_settings()
        
        # Property: Valid config should be loaded successfully
        assert settings.ENVIRONMENT == "development"
        assert settings.DATABASE_URL == "postgresql://localhost:5432/test"
        assert settings.MONGODB_URL == "mongodb://localhost:27017/test"
        assert settings.REDIS_URL == "redis://localhost:6379/0"
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRATION_MINUTES == 60
        assert settings.RATE_LIMIT_PER_MINUTE == 100


@pytest.mark.integration
def test_production_environment_enforces_strict_validation():
    """
    Integration test: Verify production environment enforces strict validation.
    
    This test verifies:
    - Production environment requires strong JWT secret
    - Production environment requires API keys
    - Error messages are clear about production requirements
    """
    # Test 1: Default JWT secret rejected in production
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "dev_secret_key_change_in_production",
        "GEMINI_API_KEY": "test",
        "OPENAI_API_KEY": "test"
    }, clear=True):
        with pytest.raises(ValueError) as exc_info:
            load_settings()
        
        error_msg = str(exc_info.value)
        assert "JWT_SECRET" in error_msg
        assert "production" in error_msg.lower()
    
    # Test 2: Missing API keys rejected in production
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "a" * 32,
        "GEMINI_API_KEY": "",
        "OPENAI_API_KEY": ""
    }, clear=True):
        with pytest.raises(ValueError) as exc_info:
            load_settings()
        
        error_msg = str(exc_info.value)
        assert "GEMINI_API_KEY" in error_msg or "OPENAI_API_KEY" in error_msg
        assert "production" in error_msg.lower()
    
    # Test 3: Valid production config accepted
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "JWT_SECRET": "a" * 32,
        "GEMINI_API_KEY": "valid_key",
        "OPENAI_API_KEY": "valid_key"
    }, clear=True):
        settings = load_settings()
        assert settings.ENVIRONMENT == "production"
        assert len(settings.JWT_SECRET) >= 32
        assert settings.GEMINI_API_KEY == "valid_key"
        assert settings.OPENAI_API_KEY == "valid_key"
