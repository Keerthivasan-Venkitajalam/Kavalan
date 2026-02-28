"""
Property-Based Test: Sensitive Configuration Encryption

Feature: production-ready-browser-extension
Property 37: Sensitive Configuration Encryption

**Validates: Requirements 17.5**

For any sensitive configuration value (API keys, database passwords), the value should:
1. Be encrypted at rest using AES-256
2. Decrypt back to the original plaintext value
3. Produce different ciphertext for the same plaintext (due to random IV)
4. Not be readable in plaintext form when encrypted
5. Use proper encryption key derivation

This property test verifies:
1. Encryption round-trip preserves original values
2. Encrypted values differ from plaintext
3. Same plaintext produces different ciphertexts (random IV)
4. Different plaintexts produce different ciphertexts
5. Encryption uses AES-256 (32-byte key)
6. Encrypted values are base64-encoded
7. Empty strings are handled correctly
8. Unicode and special characters are preserved
9. Long values are encrypted correctly
10. Wrong master key fails decryption
"""
import pytest
from hypothesis import given, strategies as st, settings, assume
from app.utils.config_encryption import (
    ConfigEncryption,
    encrypt_sensitive_config,
    decrypt_sensitive_config
)


# Strategy for generating sensitive configuration values
sensitive_values = st.one_of(
    # API keys (alphanumeric with underscores)
    st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), whitelist_characters='_-')
    ),
    # Database passwords (alphanumeric with special chars)
    st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'))
    ),
    # JWT secrets (long alphanumeric strings)
    st.text(
        min_size=32,
        max_size=128,
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'))
    ),
    # Database URLs
    st.builds(
        lambda proto, user, pwd, host, port, db: f"{proto}://{user}:{pwd}@{host}:{port}/{db}",
        proto=st.sampled_from(['postgresql', 'mongodb', 'mysql']),
        user=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        pwd=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'))),
        host=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        port=st.integers(min_value=1024, max_value=65535),
        db=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
    ),
    # Unicode strings (for internationalization)
    st.text(min_size=1, max_size=100),
    # Empty strings (edge case)
    st.just("")
)

# Strategy for generating master keys (should be 32+ characters)
master_keys = st.text(
    min_size=32,
    max_size=64,
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'P'))
)


@given(plaintext=sensitive_values, master_key=master_keys)
@settings(max_examples=100)
def test_encryption_roundtrip_preserves_plaintext(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Round-Trip)
    
    For any sensitive configuration value and master key, encrypting then
    decrypting should return the exact original plaintext.
    
    This verifies:
    - Encryption is reversible
    - No data loss during encryption/decryption
    - All character types are preserved (ASCII, Unicode, special chars)
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the plaintext
    encrypted = encryptor.encrypt(plaintext)
    
    # Decrypt back to plaintext
    decrypted = encryptor.decrypt(encrypted)
    
    # Property: Decrypted value must exactly match original plaintext
    assert decrypted == plaintext, \
        f"Round-trip failed: original='{plaintext}', decrypted='{decrypted}'"


@given(plaintext=sensitive_values.filter(lambda x: len(x) > 0), master_key=master_keys)
@settings(max_examples=100)
def test_encrypted_value_differs_from_plaintext(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Ciphertext Differs)
    
    For any non-empty sensitive value, the encrypted ciphertext should
    differ from the plaintext (i.e., encryption actually transforms the data).
    
    This verifies:
    - Encryption produces ciphertext that is not readable as plaintext
    - Sensitive values are protected at rest
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the plaintext
    encrypted = encryptor.encrypt(plaintext)
    
    # Property: Encrypted value must differ from plaintext
    assert encrypted != plaintext, \
        f"Encrypted value should differ from plaintext: '{plaintext}'"


@given(plaintext=sensitive_values, master_key=master_keys)
@settings(max_examples=100)
def test_same_plaintext_produces_different_ciphertexts(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Random IV)
    
    For any sensitive value, encrypting the same plaintext twice should
    produce different ciphertexts due to random initialization vectors (IV).
    
    This verifies:
    - Each encryption uses a unique random IV
    - Prevents pattern analysis attacks
    - Both ciphertexts decrypt to the same plaintext
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the same plaintext twice
    encrypted1 = encryptor.encrypt(plaintext)
    encrypted2 = encryptor.encrypt(plaintext)
    
    # Property: Different ciphertexts for same plaintext (unless empty)
    if plaintext:  # Empty strings may produce same result
        assert encrypted1 != encrypted2, \
            f"Same plaintext should produce different ciphertexts due to random IV"
    
    # Property: Both should decrypt to the same plaintext
    decrypted1 = encryptor.decrypt(encrypted1)
    decrypted2 = encryptor.decrypt(encrypted2)
    assert decrypted1 == plaintext, "First ciphertext should decrypt correctly"
    assert decrypted2 == plaintext, "Second ciphertext should decrypt correctly"


@given(
    plaintext1=sensitive_values.filter(lambda x: len(x) > 0),
    plaintext2=sensitive_values.filter(lambda x: len(x) > 0),
    master_key=master_keys
)
@settings(max_examples=100)
def test_different_plaintexts_produce_different_ciphertexts(
    plaintext1: str,
    plaintext2: str,
    master_key: str
):
    """
    Property 37: Sensitive Configuration Encryption (Unique Ciphertexts)
    
    For any two different plaintexts, the encrypted ciphertexts should
    be different (with high probability).
    
    This verifies:
    - Encryption is deterministic for different inputs
    - No collisions in ciphertext space
    """
    # Only test when plaintexts are actually different
    assume(plaintext1 != plaintext2)
    
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt both plaintexts
    encrypted1 = encryptor.encrypt(plaintext1)
    encrypted2 = encryptor.encrypt(plaintext2)
    
    # Property: Different plaintexts should produce different ciphertexts
    assert encrypted1 != encrypted2, \
        f"Different plaintexts should produce different ciphertexts"


@given(plaintext=sensitive_values, master_key=master_keys)
@settings(max_examples=100)
def test_encrypted_value_is_base64_encoded(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Base64 Encoding)
    
    For any sensitive value, the encrypted ciphertext should be base64-encoded
    for safe storage in configuration files.
    
    This verifies:
    - Encrypted values are text-safe (no binary data)
    - Can be stored in environment variables and config files
    - Base64 encoding is valid
    """
    import base64
    
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the plaintext
    encrypted = encryptor.encrypt(plaintext)
    
    if encrypted:  # Skip empty strings
        # Property: Encrypted value should be valid base64
        try:
            decoded = base64.b64decode(encrypted.encode('ascii'))
            # Property: Decoded data should be at least 32 bytes (16-byte IV + 16-byte min ciphertext)
            assert len(decoded) >= 32, \
                f"Encrypted data should be at least 32 bytes (IV + ciphertext), got {len(decoded)}"
        except Exception as e:
            pytest.fail(f"Encrypted value should be valid base64: {e}")


@given(plaintext=sensitive_values, master_key=master_keys)
@settings(max_examples=100)
def test_is_encrypted_correctly_identifies_encrypted_values(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Detection)
    
    For any sensitive value, the is_encrypted() method should correctly
    identify whether a value is encrypted or plaintext.
    
    This verifies:
    - Encrypted values are detected as encrypted
    - Plaintext values are detected as plaintext
    - Detection is reliable
    """
    encryptor = ConfigEncryption(master_key)
    
    # Property: Plaintext should not be detected as encrypted
    if plaintext:  # Skip empty strings
        assert encryptor.is_encrypted(plaintext) is False, \
            f"Plaintext should not be detected as encrypted: '{plaintext}'"
    
    # Encrypt the plaintext
    encrypted = encryptor.encrypt(plaintext)
    
    # Property: Encrypted value should be detected as encrypted
    if encrypted:  # Skip empty strings
        assert encryptor.is_encrypted(encrypted) is True, \
            f"Encrypted value should be detected as encrypted"


@given(plaintext=sensitive_values)
@settings(max_examples=50)
def test_convenience_functions_work_correctly(plaintext: str):
    """
    Property 37: Sensitive Configuration Encryption (Convenience Functions)
    
    For any sensitive value, the convenience functions encrypt_sensitive_config()
    and decrypt_sensitive_config() should work correctly with a master key.
    
    This verifies:
    - Convenience functions provide same functionality as class methods
    - Round-trip works through convenience functions
    """
    master_key = "test_master_key_for_convenience_functions_32chars"
    
    # Encrypt using convenience function
    encrypted = encrypt_sensitive_config(plaintext, master_key)
    
    # Decrypt using convenience function
    decrypted = decrypt_sensitive_config(encrypted, master_key)
    
    # Property: Round-trip should preserve plaintext
    assert decrypted == plaintext, \
        f"Convenience functions round-trip failed: original='{plaintext}', decrypted='{decrypted}'"


@given(
    plaintext=sensitive_values.filter(lambda x: len(x) > 0),
    master_key1=master_keys,
    master_key2=master_keys
)
@settings(max_examples=100)
def test_different_master_keys_produce_different_ciphertexts(
    plaintext: str,
    master_key1: str,
    master_key2: str
):
    """
    Property 37: Sensitive Configuration Encryption (Key Separation)
    
    For any sensitive value, encrypting with different master keys should
    produce different ciphertexts.
    
    This verifies:
    - Master key affects encryption output
    - Different keys provide isolation
    """
    # Only test when master keys are different
    assume(master_key1 != master_key2)
    
    encryptor1 = ConfigEncryption(master_key1)
    encryptor2 = ConfigEncryption(master_key2)
    
    # Encrypt with both keys
    encrypted1 = encryptor1.encrypt(plaintext)
    encrypted2 = encryptor2.encrypt(plaintext)
    
    # Property: Different master keys should produce different ciphertexts
    assert encrypted1 != encrypted2, \
        f"Different master keys should produce different ciphertexts"


@given(
    plaintext=sensitive_values.filter(lambda x: len(x) > 0),
    master_key1=master_keys,
    master_key2=master_keys
)
@settings(max_examples=100)
def test_wrong_master_key_fails_decryption(
    plaintext: str,
    master_key1: str,
    master_key2: str
):
    """
    Property 37: Sensitive Configuration Encryption (Key Verification)
    
    For any sensitive value encrypted with one master key, attempting to
    decrypt with a different master key should fail or produce garbage.
    
    This verifies:
    - Encryption is key-dependent
    - Wrong key cannot decrypt data
    - Security property: no key recovery
    """
    # Only test when master keys are different
    assume(master_key1 != master_key2)
    
    encryptor1 = ConfigEncryption(master_key1)
    encryptor2 = ConfigEncryption(master_key2)
    
    # Encrypt with first key
    encrypted = encryptor1.encrypt(plaintext)
    
    # Try to decrypt with second key
    try:
        decrypted = encryptor2.decrypt(encrypted)
        
        # Property: Decryption with wrong key should not produce original plaintext
        assert decrypted != plaintext, \
            f"Wrong master key should not decrypt to original plaintext"
    except Exception:
        # Decryption may fail with wrong key, which is acceptable
        pass


@given(plaintext=st.text(min_size=1, max_size=10000), master_key=master_keys)
@settings(max_examples=50)
def test_long_values_encrypted_correctly(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Long Values)
    
    For any long sensitive value (up to 10KB), encryption and decryption
    should work correctly.
    
    This verifies:
    - No length limitations on encrypted values
    - Large configuration values are supported
    - Padding works correctly for all lengths
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the long plaintext
    encrypted = encryptor.encrypt(plaintext)
    
    # Decrypt back
    decrypted = encryptor.decrypt(encrypted)
    
    # Property: Long values should round-trip correctly
    assert decrypted == plaintext, \
        f"Long value round-trip failed: length={len(plaintext)}"


@given(master_key=master_keys)
@settings(max_examples=50)
def test_empty_string_handled_correctly(master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Empty String)
    
    For empty strings, encryption and decryption should handle them gracefully.
    
    This verifies:
    - Edge case: empty strings are handled
    - No crashes or errors
    - Round-trip works for empty strings
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt empty string
    encrypted = encryptor.encrypt("")
    
    # Decrypt back
    decrypted = encryptor.decrypt(encrypted)
    
    # Property: Empty string should round-trip correctly
    assert decrypted == "", \
        f"Empty string round-trip failed: decrypted='{decrypted}'"


@given(
    plaintext=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(min_codepoint=0x0900, max_codepoint=0x097F)  # Devanagari (Hindi)
    ),
    master_key=master_keys
)
@settings(max_examples=50)
def test_unicode_characters_preserved(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Unicode)
    
    For any sensitive value containing Unicode characters (e.g., Hindi, Tamil),
    encryption and decryption should preserve the exact characters.
    
    This verifies:
    - Unicode support for internationalization
    - UTF-8 encoding/decoding works correctly
    - No character corruption
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the Unicode plaintext
    encrypted = encryptor.encrypt(plaintext)
    
    # Decrypt back
    decrypted = encryptor.decrypt(encrypted)
    
    # Property: Unicode characters should be preserved exactly
    assert decrypted == plaintext, \
        f"Unicode round-trip failed: original='{plaintext}', decrypted='{decrypted}'"


@given(
    plaintext=st.text(
        min_size=1,
        max_size=100,
        alphabet=st.characters(whitelist_categories=('P', 'S'))  # Punctuation and symbols
    ),
    master_key=master_keys
)
@settings(max_examples=50)
def test_special_characters_preserved(plaintext: str, master_key: str):
    """
    Property 37: Sensitive Configuration Encryption (Special Characters)
    
    For any sensitive value containing special characters and symbols,
    encryption and decryption should preserve them exactly.
    
    This verifies:
    - Special characters in passwords/keys are preserved
    - No escaping or encoding issues
    """
    encryptor = ConfigEncryption(master_key)
    
    # Encrypt the plaintext with special chars
    encrypted = encryptor.encrypt(plaintext)
    
    # Decrypt back
    decrypted = encryptor.decrypt(encrypted)
    
    # Property: Special characters should be preserved exactly
    assert decrypted == plaintext, \
        f"Special characters round-trip failed: original='{plaintext}', decrypted='{decrypted}'"


def test_aes_256_key_derivation():
    """
    Property 37: Sensitive Configuration Encryption (AES-256)
    
    Verify that the encryption uses AES-256 (32-byte key) as required.
    
    This verifies:
    - Key derivation produces 32-byte keys (256 bits)
    - AES-256 algorithm is used
    - Meets security requirements
    """
    master_key = "test_master_key_32chars_long_12345678"
    encryptor = ConfigEncryption(master_key)
    
    # Property: Encryption key should be 32 bytes (256 bits) for AES-256
    assert len(encryptor.encryption_key) == 32, \
        f"Encryption key should be 32 bytes for AES-256, got {len(encryptor.encryption_key)}"


def test_master_key_required():
    """
    Property 37: Sensitive Configuration Encryption (Master Key Required)
    
    Verify that a master key is required for encryption.
    
    This verifies:
    - Security: no default/weak keys
    - Explicit key management
    """
    import os
    
    # Clear MASTER_KEY env var if set
    old_master_key = os.environ.get("MASTER_KEY")
    if "MASTER_KEY" in os.environ:
        del os.environ["MASTER_KEY"]
    
    try:
        # Property: Creating encryptor without master key should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            ConfigEncryption()
        
        error_msg = str(exc_info.value)
        assert "MASTER_KEY" in error_msg, \
            f"Error message should mention MASTER_KEY, got: {error_msg}"
    finally:
        # Restore original env var
        if old_master_key:
            os.environ["MASTER_KEY"] = old_master_key


@pytest.mark.integration
def test_encryption_meets_aes_256_requirement():
    """
    Integration test: Verify encryption meets AES-256 requirement.
    
    This test verifies:
    - Encryption uses AES-256 algorithm
    - Key size is 256 bits (32 bytes)
    - IV size is 128 bits (16 bytes) for AES
    - Ciphertext includes IV prepended
    """
    import base64
    
    master_key = "test_master_key_for_aes_256_verification_32chars"
    encryptor = ConfigEncryption(master_key)
    
    plaintext = "test_api_key_12345"
    encrypted = encryptor.encrypt(plaintext)
    
    # Decode base64 to get raw encrypted data
    encrypted_data = base64.b64decode(encrypted.encode('ascii'))
    
    # Property: Encrypted data should have IV (16 bytes) + ciphertext
    assert len(encrypted_data) >= 32, \
        f"Encrypted data should be at least 32 bytes (16-byte IV + 16-byte min ciphertext)"
    
    # Property: IV should be 16 bytes (128 bits for AES)
    iv = encrypted_data[:16]
    assert len(iv) == 16, f"IV should be 16 bytes, got {len(iv)}"
    
    # Property: Encryption key should be 32 bytes (256 bits for AES-256)
    assert len(encryptor.encryption_key) == 32, \
        f"Encryption key should be 32 bytes for AES-256, got {len(encryptor.encryption_key)}"
