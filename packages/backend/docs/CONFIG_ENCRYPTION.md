# Configuration Encryption

This document describes how to encrypt sensitive configuration values at rest using AES-256 encryption.

## Overview

The configuration encryption system protects sensitive values like API keys, database passwords, and JWT secrets by encrypting them at rest. This ensures that even if configuration files are compromised, the sensitive values remain protected.

## Features

- **AES-256 encryption**: Industry-standard encryption algorithm
- **Automatic field detection**: Automatically encrypts known sensitive fields
- **Master key protection**: Single master key encrypts all configuration values
- **CLI tools**: Easy-to-use command-line tools for encryption/decryption
- **Transparent decryption**: Configuration values are automatically decrypted when loaded

## Sensitive Fields

The following configuration fields are automatically encrypted:

- `GEMINI_API_KEY` - Google Gemini API key
- `OPENAI_API_KEY` - OpenAI API key
- `JWT_SECRET` - JWT signing secret
- `DATABASE_URL` - PostgreSQL connection string (may contain password)
- `MONGODB_URL` - MongoDB connection string (may contain password)

## Setup

### 1. Generate a Master Key

First, generate a secure master key:

```bash
python scripts/encrypt_config.py generate-key
```

This will output a 64-character hexadecimal key. **Save this key securely!** You'll need it to decrypt your configuration files.

Example output:
```
Generated master key:
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

Save this key securely! You'll need it to decrypt your config files.
Set it as an environment variable:
export MASTER_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

### 2. Set the Master Key

Set the master key as an environment variable:

```bash
export MASTER_KEY=your_generated_key_here
```

For production deployments, store the master key in a secure secrets management system (e.g., AWS Secrets Manager, HashiCorp Vault, Kubernetes Secrets).

### 3. Encrypt Your Configuration File

Encrypt your `.env` file:

```bash
python scripts/encrypt_config.py encrypt .env .env.encrypted
```

This will create `.env.encrypted` with all sensitive fields encrypted.

Example:
```bash
# Before encryption (.env)
GEMINI_API_KEY=my_secret_api_key_12345
OPENAI_API_KEY=sk-1234567890abcdef
JWT_SECRET=my_jwt_secret_key

# After encryption (.env.encrypted)
GEMINI_API_KEY=dGVzdF9lbmNyeXB0ZWRfdmFsdWVfaGVyZQ==
OPENAI_API_KEY=YW5vdGhlcl9lbmNyeXB0ZWRfdmFsdWU=
JWT_SECRET=eWV0X2Fub3RoZXJfZW5jcnlwdGVkX3ZhbHVl
```

### 4. Use Encrypted Configuration

The application can load encrypted configuration files transparently:

```python
from app.utils.config_encryption import ConfigEncryption

# Load encrypted config
encryptor = ConfigEncryption()
config = encryptor.load_encrypted_config(Path(".env.encrypted"))

# Values are automatically decrypted
print(config["GEMINI_API_KEY"])  # Prints the decrypted value
```

## CLI Tool Usage

### Generate Master Key

```bash
python scripts/encrypt_config.py generate-key
```

Generates a new secure master key.

### Encrypt Configuration File

```bash
python scripts/encrypt_config.py encrypt <input_file> <output_file>
```

Encrypts sensitive fields in the input file and writes to the output file.

Example:
```bash
export MASTER_KEY=your_key_here
python scripts/encrypt_config.py encrypt .env .env.encrypted
```

### Decrypt Configuration File

```bash
python scripts/encrypt_config.py decrypt <input_file> <output_file>
```

Decrypts sensitive fields in the input file and writes to the output file.

Example:
```bash
export MASTER_KEY=your_key_here
python scripts/encrypt_config.py decrypt .env.encrypted .env.decrypted
```

## Programmatic Usage

### Encrypt a Single Value

```python
from app.utils.config_encryption import encrypt_sensitive_config

# Encrypt a single value
encrypted = encrypt_sensitive_config("my_secret_api_key", master_key="your_key")
print(encrypted)  # Base64-encoded encrypted value
```

### Decrypt a Single Value

```python
from app.utils.config_encryption import decrypt_sensitive_config

# Decrypt a single value
decrypted = decrypt_sensitive_config(encrypted_value, master_key="your_key")
print(decrypted)  # Original plaintext value
```

### Encrypt/Decrypt Config Files

```python
from pathlib import Path
from app.utils.config_encryption import ConfigEncryption

# Initialize with master key
encryptor = ConfigEncryption(master_key="your_key")

# Encrypt a config file
encryptor.encrypt_config_file(
    input_path=Path(".env"),
    output_path=Path(".env.encrypted")
)

# Decrypt a config file
encryptor.decrypt_config_file(
    input_path=Path(".env.encrypted"),
    output_path=Path(".env.decrypted")
)

# Load and decrypt config
config = encryptor.load_encrypted_config(Path(".env.encrypted"))
```

## Security Best Practices

### Master Key Management

1. **Never commit the master key to version control**
   - Add `.env` and master key files to `.gitignore`
   - Use environment variables or secrets management systems

2. **Use different master keys for different environments**
   - Development, staging, and production should have separate keys
   - Rotate keys periodically

3. **Store master keys securely**
   - Use AWS Secrets Manager, HashiCorp Vault, or similar
   - For Kubernetes, use Kubernetes Secrets with encryption at rest
   - For local development, use environment variables

### Configuration File Management

1. **Commit encrypted files to version control**
   - `.env.encrypted` can be safely committed
   - Never commit `.env` or `.env.decrypted` files

2. **Rotate encrypted values regularly**
   - Re-encrypt configuration files when keys change
   - Update master keys periodically

3. **Limit access to decrypted files**
   - Only decrypt configuration files when necessary
   - Delete decrypted files after use
   - Use file permissions to restrict access

## Deployment

### Docker

Set the master key as an environment variable in your Docker container:

```dockerfile
# Dockerfile
ENV MASTER_KEY=${MASTER_KEY}
```

```bash
# Build and run
docker build -t kavalan-backend .
docker run -e MASTER_KEY=your_key_here kavalan-backend
```

### Kubernetes

Store the master key in a Kubernetes Secret:

```yaml
# secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: kavalan-secrets
type: Opaque
data:
  master-key: <base64-encoded-master-key>
```

Reference it in your deployment:

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: kavalan-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: kavalan-backend:latest
        env:
        - name: MASTER_KEY
          valueFrom:
            secretKeyRef:
              name: kavalan-secrets
              key: master-key
```

### AWS

Use AWS Secrets Manager to store the master key:

```python
import boto3
import os

def get_master_key():
    """Retrieve master key from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='ap-south-1')
    response = client.get_secret_value(SecretId='kavalan/master-key')
    return response['SecretString']

# Set as environment variable
os.environ['MASTER_KEY'] = get_master_key()
```

## Troubleshooting

### Error: MASTER_KEY environment variable must be set

**Solution**: Set the `MASTER_KEY` environment variable before running the application or CLI tool.

```bash
export MASTER_KEY=your_key_here
```

### Error: Config file not found

**Solution**: Ensure the input file path is correct and the file exists.

```bash
ls -la .env.encrypted  # Check if file exists
```

### Decryption produces garbage output

**Solution**: Ensure you're using the correct master key. The master key used for decryption must match the one used for encryption.

### Values are not being encrypted

**Solution**: Check that the field name is in the `SENSITIVE_FIELDS` list. Only fields in this list are automatically encrypted.

## Technical Details

### Encryption Algorithm

- **Algorithm**: AES-256-CBC
- **Key Derivation**: PBKDF2-HMAC-SHA256 with 100,000 iterations
- **IV**: Random 16-byte initialization vector (generated per encryption)
- **Padding**: PKCS7 padding
- **Encoding**: Base64 encoding for storage

### Encrypted Value Format

Encrypted values are stored as base64-encoded strings with the following format:

```
base64(IV || ciphertext)
```

Where:
- `IV` is the 16-byte initialization vector
- `ciphertext` is the encrypted plaintext with PKCS7 padding

### Key Derivation

The master key is derived using PBKDF2-HMAC-SHA256:

```python
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,  # 256 bits for AES-256
    salt=b"kavalan_config_salt_v1",
    iterations=100000,
    backend=default_backend()
)
encryption_key = kdf.derive(master_key)
```

## References

- [NIST AES Specification](https://csrc.nist.gov/publications/detail/fips/197/final)
- [PBKDF2 RFC 2898](https://tools.ietf.org/html/rfc2898)
- [Cryptography Library Documentation](https://cryptography.io/)
