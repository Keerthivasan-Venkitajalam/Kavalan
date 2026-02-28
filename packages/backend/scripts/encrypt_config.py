#!/usr/bin/env python
"""
CLI tool for encrypting and decrypting configuration files
Usage:
    python scripts/encrypt_config.py encrypt .env .env.encrypted
    python scripts/encrypt_config.py decrypt .env.encrypted .env.decrypted
    python scripts/encrypt_config.py generate-key
"""
import sys
import secrets
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.config_encryption import ConfigEncryption


def print_usage():
    """Print usage information"""
    print("Usage:")
    print("  Encrypt config file:")
    print("    python scripts/encrypt_config.py encrypt <input_file> <output_file>")
    print()
    print("  Decrypt config file:")
    print("    python scripts/encrypt_config.py decrypt <input_file> <output_file>")
    print()
    print("  Generate master key:")
    print("    python scripts/encrypt_config.py generate-key")
    print()
    print("Environment Variables:")
    print("  MASTER_KEY - Master encryption key (required for encrypt/decrypt)")
    print()
    print("Examples:")
    print("  # Generate a master key")
    print("  python scripts/encrypt_config.py generate-key")
    print()
    print("  # Encrypt a config file")
    print("  export MASTER_KEY=your_generated_key")
    print("  python scripts/encrypt_config.py encrypt .env .env.encrypted")
    print()
    print("  # Decrypt a config file")
    print("  export MASTER_KEY=your_generated_key")
    print("  python scripts/encrypt_config.py decrypt .env.encrypted .env.decrypted")


def generate_key():
    """Generate a secure master key"""
    key = secrets.token_hex(32)
    print("Generated master key:")
    print(key)
    print()
    print("Save this key securely! You'll need it to decrypt your config files.")
    print("Set it as an environment variable:")
    print(f"export MASTER_KEY={key}")


def encrypt_file(input_path: str, output_path: str):
    """Encrypt a config file"""
    try:
        encryptor = ConfigEncryption()
        
        input_file = Path(input_path)
        output_file = Path(output_path)
        
        if not input_file.exists():
            print(f"Error: Input file not found: {input_path}")
            sys.exit(1)
        
        print(f"Encrypting {input_path} -> {output_path}")
        encryptor.encrypt_config_file(input_file, output_file)
        print("✓ Encryption complete!")
        print()
        print("Encrypted fields:")
        for field in sorted(ConfigEncryption.SENSITIVE_FIELDS):
            print(f"  - {field}")
        
    except ValueError as e:
        print(f"Error: {e}")
        print()
        print("Make sure MASTER_KEY environment variable is set.")
        print("Generate a key with: python scripts/encrypt_config.py generate-key")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def decrypt_file(input_path: str, output_path: str):
    """Decrypt a config file"""
    try:
        encryptor = ConfigEncryption()
        
        input_file = Path(input_path)
        output_file = Path(output_path)
        
        if not input_file.exists():
            print(f"Error: Input file not found: {input_path}")
            sys.exit(1)
        
        print(f"Decrypting {input_path} -> {output_path}")
        encryptor.decrypt_config_file(input_file, output_file)
        print("✓ Decryption complete!")
        print()
        print("⚠️  Warning: The decrypted file contains sensitive information.")
        print("   Keep it secure and do not commit it to version control.")
        
    except ValueError as e:
        print(f"Error: {e}")
        print()
        print("Make sure MASTER_KEY environment variable is set.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "generate-key":
        generate_key()
    elif command == "encrypt":
        if len(sys.argv) != 4:
            print("Error: encrypt command requires input and output file paths")
            print()
            print_usage()
            sys.exit(1)
        encrypt_file(sys.argv[2], sys.argv[3])
    elif command == "decrypt":
        if len(sys.argv) != 4:
            print("Error: decrypt command requires input and output file paths")
            print()
            print_usage()
            sys.exit(1)
        decrypt_file(sys.argv[2], sys.argv[3])
    else:
        print(f"Error: Unknown command: {command}")
        print()
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
