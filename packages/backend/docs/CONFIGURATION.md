# Configuration Management

This document describes the configuration management system for the Kavalan backend services.

## Overview

The configuration system supports:
- **Multiple environments**: development, staging, production, test
- **Environment variables**: Override any setting via environment variables
- **Config files**: Environment-specific `.env` files
- **Priority-based loading**: Environment variables > environment-specific files > base files > defaults

## Configuration Loading Priority

Settings are loaded in the following order (highest priority first):

1. **Environment variables** - Highest priority
2. **Environment-specific config file** - `.env.{ENVIRONMENT}`
3. **Base config file** - `.env`
4. **Default values** - Lowest priority

## Environment Types

The system supports four environment types:

- `development` - Local development
- `staging` - Staging/QA environment
- `production` - Production environment
- `test` - Testing environment

## Configuration Files

### Base Configuration

Create a `.env` file in the `packages/backend` directory for base configuration:

```bash
# .env
ENVIRONMENT=development
DATABASE_URL=postgresql://localhost:5432/kavalan
MONGODB_URL=mongodb://localhost:27017/kavalan
REDIS_URL=redis://localhost:6379/0
```

### Environment-Specific Configuration

Create environment-specific files to override settings:

- `.env.development` - Development overrides
- `.env.staging` - Staging overrides
- `.env.production` - Production overrides
- `.env.test` - Test overrides

Example `.env.production`:

```bash
# .env.production
ENVIRONMENT=production
DATABASE_URL=postgresql://prod-user:secure-password@prod-db:5432/kavalan
MONGODB_URL=mongodb://prod-user:secure-password@prod-mongo:27017/kavalan
REDIS_URL=redis://prod-redis:6379/0
GEMINI_API_KEY=your_production_api_key
JWT_SECRET=your_strong_production_secret
CORS_ORIGINS=chrome-extension://prod-extension-id,https://kavalan.in
RATE_LIMIT_PER_MINUTE=60
```

## Available Settings

### Environment

- `ENVIRONMENT` - Environment type (development, staging, production, test)
  - Default: `development`

### Database URLs

- `DATABASE_URL` - PostgreSQL connection string
  - Default: `postgresql://localhost:5432/kavalan`
  
- `MONGODB_URL` - MongoDB connection string
  - Default: `mongodb://localhost:27017/kavalan`
  
- `REDIS_URL` - Redis connection string
  - Default: `redis://localhost:6379/0`

### API Keys

- `GEMINI_API_KEY` - Google Gemini API key
  - Default: `""` (empty)
  
- `OPENAI_API_KEY` - OpenAI API key
  - Default: `""` (empty)

### JWT Configuration

- `JWT_SECRET` - Secret key for JWT signing
  - Default: `dev_secret_key_change_in_production`
  - **IMPORTANT**: Change this in production!
  
- `JWT_ALGORITHM` - JWT signing algorithm
  - Default: `HS256`
  
- `JWT_EXPIRATION_MINUTES` - JWT token expiration time
  - Default: `60`

### CORS Configuration

- `CORS_ORIGINS` - Allowed CORS origins (comma-separated)
  - Default: `*` (allow all)
  - Example: `chrome-extension://abc123,https://example.com`

### Rate Limiting

- `RATE_LIMIT_PER_MINUTE` - Maximum requests per minute per user
  - Default: `60`

### Celery Configuration

- `CELERY_BROKER_URL` - Celery message broker URL
  - Default: `redis://localhost:6379/0`
  
- `CELERY_RESULT_BACKEND` - Celery result backend URL
  - Default: `redis://localhost:6379/0`

## Usage

### In Python Code

```python
from app.config import settings

# Access configuration values
database_url = settings.DATABASE_URL
api_key = settings.GEMINI_API_KEY
environment = settings.ENVIRONMENT

# Check environment
if settings.ENVIRONMENT == "production":
    # Production-specific logic
    pass
```

### Loading Settings Programmatically

```python
from app.config import load_settings, get_config_file_path

# Load settings with current environment
settings = load_settings()

# Get path to environment-specific config file
config_path = get_config_file_path("production")
print(f"Production config: {config_path}")
```

### Setting Environment

Set the `ENVIRONMENT` variable before starting the application:

```bash
# Development (default)
python -m uvicorn app.main:app

# Staging
ENVIRONMENT=staging python -m uvicorn app.main:app

# Production
ENVIRONMENT=production python -m uvicorn app.main:app
```

### Docker Deployment

In Docker, set environment variables in `docker-compose.yml`:

```yaml
services:
  backend:
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://prod-db:5432/kavalan
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - JWT_SECRET=${JWT_SECRET}
```

Or use an environment file:

```yaml
services:
  backend:
    env_file:
      - .env.production
```

## Best Practices

### Security

1. **Never commit sensitive values** to version control
   - Use `.gitignore` to exclude `.env` files
   - Store secrets in environment variables or secret management systems

2. **Use strong secrets in production**
   - Generate strong `JWT_SECRET` values
   - Rotate secrets regularly

3. **Restrict CORS origins**
   - Never use `*` in production
   - Specify exact extension IDs and domains

### Environment Management

1. **Use environment-specific files**
   - Keep development settings in `.env.development`
   - Keep production settings in `.env.production`
   - Never mix environments

2. **Document required settings**
   - Provide `.env.example` files
   - Document all required API keys

3. **Validate configuration**
   - Check for missing required values at startup
   - Use type hints for configuration values

### Development Workflow

1. **Local development**
   ```bash
   # Copy example config
   cp .env.example .env.development
   
   # Edit with your local values
   vim .env.development
   
   # Run with development config
   ENVIRONMENT=development python -m uvicorn app.main:app
   ```

2. **Testing**
   ```bash
   # Use test environment
   ENVIRONMENT=test python -m pytest
   ```

3. **Staging deployment**
   ```bash
   # Deploy with staging config
   ENVIRONMENT=staging docker-compose up
   ```

## Troubleshooting

### Configuration not loading

1. Check that `ENVIRONMENT` variable is set correctly
2. Verify config file exists: `.env.{ENVIRONMENT}`
3. Check file permissions (must be readable)
4. Verify environment variable names are uppercase

### Values not overriding

Remember the priority order:
1. Environment variables (highest)
2. Environment-specific file
3. Base file
4. Defaults (lowest)

### CORS issues

If CORS is not working:
1. Check `CORS_ORIGINS` is set correctly
2. Ensure origins are comma-separated
3. Include protocol (https://) in origins
4. For extensions, use full extension ID

### Database connection failures

1. Verify database URLs are correct
2. Check database is running and accessible
3. Verify credentials are correct
4. Check network connectivity

## Examples

### Development Setup

```bash
# .env.development
ENVIRONMENT=development
DATABASE_URL=postgresql://localhost:5432/kavalan
MONGODB_URL=mongodb://localhost:27017/kavalan
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=dev_key_here
OPENAI_API_KEY=dev_key_here
JWT_SECRET=dev_secret
CORS_ORIGINS=*
RATE_LIMIT_PER_MINUTE=1000
```

### Production Setup

```bash
# .env.production
ENVIRONMENT=production
DATABASE_URL=postgresql://prod_user:${DB_PASSWORD}@prod-db:5432/kavalan
MONGODB_URL=mongodb://prod_user:${MONGO_PASSWORD}@prod-mongo:27017/kavalan
REDIS_URL=redis://:${REDIS_PASSWORD}@prod-redis:6379/0
GEMINI_API_KEY=${GEMINI_API_KEY}
OPENAI_API_KEY=${OPENAI_API_KEY}
JWT_SECRET=${JWT_SECRET}
CORS_ORIGINS=chrome-extension://prod-ext-id,https://kavalan.in
RATE_LIMIT_PER_MINUTE=60
```

### Testing Setup

```bash
# .env.test
ENVIRONMENT=test
DATABASE_URL=postgresql://test_user:test_pass@localhost:5432/kavalan_test
MONGODB_URL=mongodb://test_user:test_pass@localhost:27017/kavalan_test
REDIS_URL=redis://localhost:6379/1
JWT_SECRET=test_secret
CORS_ORIGINS=*
RATE_LIMIT_PER_MINUTE=10000
```

## Migration from Old Config

If you're migrating from the old configuration system:

1. **Rename your `.env` file** to `.env.development`
2. **Create environment-specific files** for staging and production
3. **Update imports** if you were importing `Settings` directly
4. **Test configuration loading** in each environment

The new system is backward compatible - existing `.env` files will still work as base configuration.
