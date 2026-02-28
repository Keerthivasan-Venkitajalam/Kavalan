"""
Configuration encryption utilities for sensitive values
Encrypts API keys and passwords at rest using AES-256
"""
import os
import base64
from pathlib import Path
from typing import Optional
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class ConfigEncryption:
    """Handles encryption and decryption of sensitive configuration values"""
    
    # Sensitive field names that should be encrypted
    SENSITIVE_FIELDS = {
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "JWT_SECRET",
        "DATABASE_URL",
        "MONGODB_URL"
    }
    
    def __init__(self, master_key: Optional[str] = None):
        """Initialize config encryption with master key
        
        Args:
            master_key: Master encryption key. If None, reads from MASTER_KEY env var
                       or generates a new key (not recommended for production)
        """
        if master_key is None:
            master_key = os.getenv("MASTER_KEY")
            if master_key is None:
                raise ValueError(
                    "MASTER_KEY environment variable must be set for config encryption. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
                )
        
        self.master_key = master_key.encode() if isinstance(master_key, str) else master_key
        
        # Derive encryption key from master key using PBKDF2
        # Use a fixed salt for config encryption (not ideal but acceptable for this use case)
        salt = b"kavalan_config_salt_v1"
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        self.encryption_key = kdf.derive(self.master_key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt a plaintext value using AES-256-CBC
        
        Args:
            plaintext: The plaintext value to encrypt
            
        Returns:
            Base64-encoded encrypted value with IV prepended
            Format: base64(iv + ciphertext)
        """
        if not plaintext:
            return ""
        
        # Generate random IV (16 bytes for AES)
        iv = os.urandom(16)
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad plaintext to multiple of 16 bytes (PKCS7 padding)
        plaintext_bytes = plaintext.encode('utf-8')
        padding_length = 16 - (len(plaintext_bytes) % 16)
        padded_plaintext = plaintext_bytes + bytes([padding_length] * padding_length)
        
        # Encrypt
        ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()
        
        # Prepend IV to ciphertext and encode as base64
        encrypted_data = iv + ciphertext
        return base64.b64encode(encrypted_data).decode('ascii')
    
    def decrypt(self, encrypted_value: str) -> str:
        """Decrypt an encrypted value
        
        Args:
            encrypted_value: Base64-encoded encrypted value with IV prepended
            
        Returns:
            Decrypted plaintext value
        """
        if not encrypted_value:
            return ""
        
        # Decode from base64
        encrypted_data = base64.b64decode(encrypted_value.encode('ascii'))
        
        # Extract IV (first 16 bytes) and ciphertext
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        
        # Create cipher
        cipher = Cipher(
            algorithms.AES(self.encryption_key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        
        # Decrypt
        padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
        
        # Remove PKCS7 padding
        padding_length = padded_plaintext[-1]
        plaintext_bytes = padded_plaintext[:-padding_length]
        
        return plaintext_bytes.decode('utf-8')
    
    def is_encrypted(self, value: str) -> bool:
        """Check if a value appears to be encrypted
        
        Args:
            value: The value to check
            
        Returns:
            True if the value appears to be encrypted (base64 with correct length)
        """
        if not value:
            return False
        
        try:
            # Try to decode as base64
            decoded = base64.b64decode(value.encode('ascii'))
            # Encrypted values should be at least 32 bytes (16 byte IV + 16 byte min ciphertext)
            return len(decoded) >= 32
        except Exception:
            return False
    
    def encrypt_config_file(self, input_path: Path, output_path: Path) -> None:
        """Encrypt sensitive values in a config file
        
        Args:
            input_path: Path to plaintext config file
            output_path: Path to write encrypted config file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Config file not found: {input_path}")
        
        encrypted_lines = []
        
        with open(input_path, 'r') as f:
            for line in f:
                line = line.rstrip('\n')
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    encrypted_lines.append(line)
                    continue
                
                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Encrypt sensitive fields
                    if key in self.SENSITIVE_FIELDS and value and not self.is_encrypted(value):
                        encrypted_value = self.encrypt(value)
                        encrypted_lines.append(f"{key}={encrypted_value}")
                    else:
                        encrypted_lines.append(line)
                else:
                    encrypted_lines.append(line)
        
        # Write encrypted config
        with open(output_path, 'w') as f:
            f.write('\n'.join(encrypted_lines) + '\n')
    
    def decrypt_config_file(self, input_path: Path, output_path: Path) -> None:
        """Decrypt sensitive values in a config file
        
        Args:
            input_path: Path to encrypted config file
            output_path: Path to write decrypted config file
        """
        if not input_path.exists():
            raise FileNotFoundError(f"Config file not found: {input_path}")
        
        decrypted_lines = []
        
        with open(input_path, 'r') as f:
            for line in f:
                line = line.rstrip('\n')
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    decrypted_lines.append(line)
                    continue
                
                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Decrypt sensitive fields
                    if key in self.SENSITIVE_FIELDS and value and self.is_encrypted(value):
                        decrypted_value = self.decrypt(value)
                        decrypted_lines.append(f"{key}={decrypted_value}")
                    else:
                        decrypted_lines.append(line)
                else:
                    decrypted_lines.append(line)
        
        # Write decrypted config
        with open(output_path, 'w') as f:
            f.write('\n'.join(decrypted_lines) + '\n')
    
    def load_encrypted_config(self, config_path: Path) -> dict:
        """Load and decrypt a config file
        
        Args:
            config_path: Path to encrypted config file
            
        Returns:
            Dictionary of decrypted config values
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        
        config = {}
        
        with open(config_path, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                
                # Parse key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Decrypt sensitive fields
                    if key in self.SENSITIVE_FIELDS and value and self.is_encrypted(value):
                        config[key] = self.decrypt(value)
                    else:
                        config[key] = value
        
        return config


def encrypt_sensitive_config(plaintext_value: str, master_key: Optional[str] = None) -> str:
    """Convenience function to encrypt a single sensitive config value
    
    Args:
        plaintext_value: The plaintext value to encrypt
        master_key: Master encryption key (optional, reads from env if not provided)
        
    Returns:
        Encrypted value as base64 string
    """
    encryptor = ConfigEncryption(master_key)
    return encryptor.encrypt(plaintext_value)


def decrypt_sensitive_config(encrypted_value: str, master_key: Optional[str] = None) -> str:
    """Convenience function to decrypt a single sensitive config value
    
    Args:
        encrypted_value: The encrypted value to decrypt
        master_key: Master encryption key (optional, reads from env if not provided)
        
    Returns:
        Decrypted plaintext value
    """
    encryptor = ConfigEncryption(master_key)
    return encryptor.decrypt(encrypted_value)
