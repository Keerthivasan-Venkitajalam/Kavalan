"""
Unit tests for configuration encryption
Tests encryption and decryption of sensitive config values
"""
import os
import tempfile
from pathlib import Path
import pytest
from app.utils.config_encryption import (
    ConfigEncryption,
    encrypt_sensitive_config,
    decrypt_sensitive_config
)


class TestConfigEncryption:
    """Test configuration encryption and decryption"""
    
    @pytest.fixture
    def master_key(self):
        """Provide a test master key"""
        return "test_master_key_for_encryption_32chars_long_12345678"
    
    @pytest.fixture
    def encryptor(self, master_key):
        """Provide a ConfigEncryption instance"""
        return ConfigEncryption(master_key)
    
    def test_encrypt_decrypt_roundtrip(self, encryptor):
        """Test that encryption and decryption preserve the original value"""
        plaintext = "my_secret_api_key_12345"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypted_value_differs_from_plaintext(self, encryptor):
        """Test that encrypted value is different from plaintext"""
        plaintext = "my_secret_api_key"
        
        encrypted = encryptor.encrypt(plaintext)
        
        assert encrypted != plaintext
    
    def test_empty_string_encryption(self, encryptor):
        """Test that empty strings are handled correctly"""
        encrypted = encryptor.encrypt("")
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == ""
    
    def test_long_value_encryption(self, encryptor):
        """Test encryption of long values"""
        plaintext = "a" * 1000
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_special_characters_encryption(self, encryptor):
        """Test encryption of values with special characters"""
        plaintext = "key!@#$%^&*()_+-=[]{}|;:',.<>?/~`"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_unicode_encryption(self, encryptor):
        """Test encryption of unicode values"""
        plaintext = "मेरा_गुप्त_कुंजी_🔐"
        
        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_different_plaintexts_produce_different_ciphertexts(self, encryptor):
        """Test that different plaintexts produce different ciphertexts"""
        plaintext1 = "secret_key_1"
        plaintext2 = "secret_key_2"
        
        encrypted1 = encryptor.encrypt(plaintext1)
        encrypted2 = encryptor.encrypt(plaintext2)
        
        assert encrypted1 != encrypted2
    
    def test_same_plaintext_produces_different_ciphertexts(self, encryptor):
        """Test that encrypting the same plaintext twice produces different ciphertexts (due to random IV)"""
        plaintext = "secret_key"
        
        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)
        
        # Different IVs should produce different ciphertexts
        assert encrypted1 != encrypted2
        
        # But both should decrypt to the same plaintext
        assert encryptor.decrypt(encrypted1) == plaintext
        assert encryptor.decrypt(encrypted2) == plaintext
    
    def test_is_encrypted_detects_encrypted_values(self, encryptor):
        """Test that is_encrypted correctly identifies encrypted values"""
        plaintext = "my_secret_key"
        encrypted = encryptor.encrypt(plaintext)
        
        assert encryptor.is_encrypted(encrypted) is True
        assert encryptor.is_encrypted(plaintext) is False
    
    def test_is_encrypted_handles_empty_string(self, encryptor):
        """Test that is_encrypted handles empty strings"""
        assert encryptor.is_encrypted("") is False
    
    def test_is_encrypted_handles_invalid_base64(self, encryptor):
        """Test that is_encrypted handles invalid base64"""
        assert encryptor.is_encrypted("not_base64!@#$") is False
    
    def test_master_key_required(self):
        """Test that master key is required"""
        # Clear MASTER_KEY env var if set
        old_master_key = os.environ.get("MASTER_KEY")
        if "MASTER_KEY" in os.environ:
            del os.environ["MASTER_KEY"]
        
        try:
            with pytest.raises(ValueError) as exc_info:
                ConfigEncryption()
            assert "MASTER_KEY environment variable must be set" in str(exc_info.value)
        finally:
            # Restore original env var
            if old_master_key:
                os.environ["MASTER_KEY"] = old_master_key
    
    def test_master_key_from_env_var(self):
        """Test that master key can be read from environment variable"""
        master_key = "test_key_from_env_32chars_long_1234567890"
        os.environ["MASTER_KEY"] = master_key
        
        try:
            encryptor = ConfigEncryption()
            plaintext = "test_value"
            
            encrypted = encryptor.encrypt(plaintext)
            decrypted = encryptor.decrypt(encrypted)
            
            assert decrypted == plaintext
        finally:
            del os.environ["MASTER_KEY"]
    
    def test_different_master_keys_produce_different_results(self):
        """Test that different master keys produce different encrypted values"""
        plaintext = "secret_value"
        
        encryptor1 = ConfigEncryption("master_key_1_32chars_long_12345678901234")
        encryptor2 = ConfigEncryption("master_key_2_32chars_long_12345678901234")
        
        encrypted1 = encryptor1.encrypt(plaintext)
        encrypted2 = encryptor2.encrypt(plaintext)
        
        # Different master keys should produce different ciphertexts
        assert encrypted1 != encrypted2
        
        # Each should decrypt correctly with its own key
        assert encryptor1.decrypt(encrypted1) == plaintext
        assert encryptor2.decrypt(encrypted2) == plaintext
    
    def test_wrong_master_key_fails_decryption(self):
        """Test that decryption with wrong master key fails or produces garbage"""
        plaintext = "secret_value"
        
        encryptor1 = ConfigEncryption("master_key_1_32chars_long_12345678901234")
        encryptor2 = ConfigEncryption("master_key_2_32chars_long_12345678901234")
        
        encrypted = encryptor1.encrypt(plaintext)
        
        # Decrypting with wrong key should not produce original plaintext
        try:
            decrypted = encryptor2.decrypt(encrypted)
            assert decrypted != plaintext
        except Exception:
            # Decryption may fail with wrong key, which is acceptable
            pass


class TestConfigFileEncryption:
    """Test encryption and decryption of config files"""
    
    @pytest.fixture
    def master_key(self):
        """Provide a test master key"""
        return "test_master_key_for_encryption_32chars_long_12345678"
    
    @pytest.fixture
    def encryptor(self, master_key):
        """Provide a ConfigEncryption instance"""
        return ConfigEncryption(master_key)
    
    @pytest.fixture
    def sample_config_content(self):
        """Provide sample config file content"""
        return """# Sample configuration file
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@localhost:5432/db
MONGODB_URL=mongodb://localhost:27017/db
REDIS_URL=redis://localhost:6379/0
GEMINI_API_KEY=my_gemini_api_key_12345
OPENAI_API_KEY=my_openai_api_key_67890
JWT_SECRET=my_jwt_secret_key_32chars_long
RATE_LIMIT_PER_MINUTE=100
"""
    
    def test_encrypt_config_file(self, encryptor, sample_config_content):
        """Test encrypting a config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "config.env"
            output_path = Path(tmpdir) / "config.encrypted.env"
            
            # Write sample config
            input_path.write_text(sample_config_content)
            
            # Encrypt config file
            encryptor.encrypt_config_file(input_path, output_path)
            
            # Read encrypted config
            encrypted_content = output_path.read_text()
            
            # Verify sensitive fields are encrypted
            assert "my_gemini_api_key_12345" not in encrypted_content
            assert "my_openai_api_key_67890" not in encrypted_content
            assert "my_jwt_secret_key_32chars_long" not in encrypted_content
            assert "postgresql://user:pass@localhost:5432/db" not in encrypted_content
            
            # Verify non-sensitive fields are not encrypted
            assert "ENVIRONMENT=production" in encrypted_content
            assert "RATE_LIMIT_PER_MINUTE=100" in encrypted_content
            
            # Verify comments are preserved
            assert "# Sample configuration file" in encrypted_content
    
    def test_decrypt_config_file(self, encryptor, sample_config_content):
        """Test decrypting a config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "config.env"
            encrypted_path = Path(tmpdir) / "config.encrypted.env"
            decrypted_path = Path(tmpdir) / "config.decrypted.env"
            
            # Write sample config
            input_path.write_text(sample_config_content)
            
            # Encrypt then decrypt
            encryptor.encrypt_config_file(input_path, encrypted_path)
            encryptor.decrypt_config_file(encrypted_path, decrypted_path)
            
            # Read decrypted config
            decrypted_content = decrypted_path.read_text()
            
            # Verify decrypted content matches original
            assert "GEMINI_API_KEY=my_gemini_api_key_12345" in decrypted_content
            assert "OPENAI_API_KEY=my_openai_api_key_67890" in decrypted_content
            assert "JWT_SECRET=my_jwt_secret_key_32chars_long" in decrypted_content
            assert "DATABASE_URL=postgresql://user:pass@localhost:5432/db" in decrypted_content
    
    def test_load_encrypted_config(self, encryptor, sample_config_content):
        """Test loading and decrypting a config file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "config.env"
            encrypted_path = Path(tmpdir) / "config.encrypted.env"
            
            # Write and encrypt sample config
            input_path.write_text(sample_config_content)
            encryptor.encrypt_config_file(input_path, encrypted_path)
            
            # Load encrypted config
            config = encryptor.load_encrypted_config(encrypted_path)
            
            # Verify values are decrypted
            assert config["GEMINI_API_KEY"] == "my_gemini_api_key_12345"
            assert config["OPENAI_API_KEY"] == "my_openai_api_key_67890"
            assert config["JWT_SECRET"] == "my_jwt_secret_key_32chars_long"
            assert config["DATABASE_URL"] == "postgresql://user:pass@localhost:5432/db"
            assert config["ENVIRONMENT"] == "production"
            assert config["RATE_LIMIT_PER_MINUTE"] == "100"
    
    def test_encrypt_config_file_not_found(self, encryptor):
        """Test that encrypting non-existent file raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "nonexistent.env"
            output_path = Path(tmpdir) / "output.env"
            
            with pytest.raises(FileNotFoundError):
                encryptor.encrypt_config_file(input_path, output_path)
    
    def test_decrypt_config_file_not_found(self, encryptor):
        """Test that decrypting non-existent file raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "nonexistent.env"
            output_path = Path(tmpdir) / "output.env"
            
            with pytest.raises(FileNotFoundError):
                encryptor.decrypt_config_file(input_path, output_path)
    
    def test_load_encrypted_config_not_found(self, encryptor):
        """Test that loading non-existent config file raises error"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nonexistent.env"
            
            with pytest.raises(FileNotFoundError):
                encryptor.load_encrypted_config(config_path)
    
    def test_encrypt_already_encrypted_values_skipped(self, encryptor, sample_config_content):
        """Test that already encrypted values are not re-encrypted"""
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = Path(tmpdir) / "config.env"
            encrypted_path = Path(tmpdir) / "config.encrypted.env"
            double_encrypted_path = Path(tmpdir) / "config.double.env"
            
            # Write and encrypt sample config
            input_path.write_text(sample_config_content)
            encryptor.encrypt_config_file(input_path, encrypted_path)
            
            # Try to encrypt again
            encryptor.encrypt_config_file(encrypted_path, double_encrypted_path)
            
            # Both encrypted files should be identical (no double encryption)
            assert encrypted_path.read_text() == double_encrypted_path.read_text()


class TestConvenienceFunctions:
    """Test convenience functions for encryption/decryption"""
    
    @pytest.fixture
    def master_key(self):
        """Provide a test master key"""
        return "test_master_key_for_encryption_32chars_long_12345678"
    
    def test_encrypt_sensitive_config(self, master_key):
        """Test encrypt_sensitive_config convenience function"""
        plaintext = "my_secret_value"
        
        encrypted = encrypt_sensitive_config(plaintext, master_key)
        
        # Verify it's encrypted
        assert encrypted != plaintext
        assert len(encrypted) > 0
    
    def test_decrypt_sensitive_config(self, master_key):
        """Test decrypt_sensitive_config convenience function"""
        plaintext = "my_secret_value"
        
        encrypted = encrypt_sensitive_config(plaintext, master_key)
        decrypted = decrypt_sensitive_config(encrypted, master_key)
        
        assert decrypted == plaintext
    
    def test_convenience_functions_roundtrip(self, master_key):
        """Test that convenience functions work together"""
        plaintext = "test_api_key_12345"
        
        encrypted = encrypt_sensitive_config(plaintext, master_key)
        decrypted = decrypt_sensitive_config(encrypted, master_key)
        
        assert decrypted == plaintext
