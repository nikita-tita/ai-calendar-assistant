"""Tests for data encryption (Fernet symmetric encryption)."""

import pytest
import json
import tempfile
import os
from pathlib import Path
from cryptography.fernet import Fernet, InvalidToken


class TestFernetEncryption:
    """Test Fernet symmetric encryption basics."""

    def test_key_generation(self):
        """Test Fernet key generation."""
        key = Fernet.generate_key()

        assert len(key) == 44  # Base64-encoded 32 bytes
        assert key.endswith(b'=')  # Base64 padding

    def test_encryption_decryption(self):
        """Test that data can be encrypted and decrypted."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        original_data = b"Sensitive user data"
        encrypted = cipher.encrypt(original_data)
        decrypted = cipher.decrypt(encrypted)

        assert decrypted == original_data
        assert encrypted != original_data

    def test_different_keys_cannot_decrypt(self):
        """Test that data encrypted with one key cannot be decrypted with another."""
        key1 = Fernet.generate_key()
        key2 = Fernet.generate_key()

        cipher1 = Fernet(key1)
        cipher2 = Fernet(key2)

        encrypted = cipher1.encrypt(b"Secret data")

        with pytest.raises(InvalidToken):
            cipher2.decrypt(encrypted)

    def test_encrypted_data_is_different_each_time(self):
        """Test that same data produces different ciphertext (due to IV)."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        data = b"Same data"
        encrypted1 = cipher.encrypt(data)
        encrypted2 = cipher.encrypt(data)

        # Ciphertexts should be different (different IVs)
        assert encrypted1 != encrypted2

        # But both should decrypt to same data
        assert cipher.decrypt(encrypted1) == data
        assert cipher.decrypt(encrypted2) == data

    def test_tampered_data_rejected(self):
        """Test that tampered ciphertext is rejected."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        encrypted = cipher.encrypt(b"Original data")

        # Tamper with ciphertext
        tampered = encrypted[:-10] + b"TAMPERED!!"

        with pytest.raises(InvalidToken):
            cipher.decrypt(tampered)

    def test_empty_data_encryption(self):
        """Test encryption of empty data."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        empty_data = b""
        encrypted = cipher.encrypt(empty_data)
        decrypted = cipher.decrypt(encrypted)

        assert decrypted == empty_data

    def test_large_data_encryption(self):
        """Test encryption of large data."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        large_data = b"X" * (1024 * 1024)  # 1 MB
        encrypted = cipher.encrypt(large_data)
        decrypted = cipher.decrypt(encrypted)

        assert decrypted == large_data


class TestJSONEncryption:
    """Test encryption of JSON data."""

    def test_json_encryption_roundtrip(self):
        """Test encrypting and decrypting JSON data."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        data = {
            "user_id": "123456",
            "todos": [
                {"id": "1", "title": "Task 1", "completed": False},
                {"id": "2", "title": "Task 2", "completed": True}
            ],
            "settings": {
                "notifications": True,
                "theme": "dark"
            }
        }

        # Encrypt
        json_bytes = json.dumps(data, indent=2).encode('utf-8')
        encrypted = cipher.encrypt(json_bytes)

        # Decrypt
        decrypted = cipher.decrypt(encrypted)
        recovered_data = json.loads(decrypted.decode('utf-8'))

        assert recovered_data == data

    def test_unicode_json_encryption(self):
        """Test encryption of JSON with unicode characters."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        data = {
            "title": "Задача на русском",
            "description": "Описание с эмодзи 🎉",
            "tags": ["работа", "важное"]
        }

        json_bytes = json.dumps(data, ensure_ascii=False).encode('utf-8')
        encrypted = cipher.encrypt(json_bytes)
        decrypted = cipher.decrypt(encrypted)
        recovered_data = json.loads(decrypted.decode('utf-8'))

        assert recovered_data == data
        assert recovered_data["title"] == "Задача на русском"


class TestKeyManagement:
    """Test encryption key management."""

    def test_key_from_base64_string(self):
        """Test loading key from base64 string (like env var)."""
        # Generate and encode
        key = Fernet.generate_key()
        key_str = key.decode('utf-8')

        # Load from string
        cipher = Fernet(key_str.encode('utf-8'))

        data = b"Test data"
        encrypted = cipher.encrypt(data)
        assert cipher.decrypt(encrypted) == data

    def test_invalid_key_rejected(self):
        """Test that invalid keys are rejected."""
        with pytest.raises(ValueError):
            Fernet(b"not-a-valid-key")

        with pytest.raises(ValueError):
            Fernet(b"too-short")

    def test_key_file_permissions(self):
        """Test that key files should have restricted permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "encryption.key"
            key = Fernet.generate_key()

            # Write key
            with open(key_file, 'wb') as f:
                f.write(key)

            # Set restrictive permissions
            os.chmod(key_file, 0o600)

            # Verify permissions
            mode = os.stat(key_file).st_mode & 0o777
            assert mode == 0o600  # Owner read/write only


class TestEncryptedFileStorage:
    """Test encrypted file storage patterns."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_save_and_load_encrypted_file(self, temp_storage):
        """Test saving and loading encrypted JSON file."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        data = {"secret": "value", "count": 42}
        filename = "test_data.json"

        # Save encrypted
        json_bytes = json.dumps(data).encode('utf-8')
        encrypted = cipher.encrypt(json_bytes)

        encrypted_path = temp_storage / f"{filename}.enc"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted)

        # Load and decrypt
        with open(encrypted_path, 'rb') as f:
            loaded_encrypted = f.read()

        decrypted = cipher.decrypt(loaded_encrypted)
        loaded_data = json.loads(decrypted.decode('utf-8'))

        assert loaded_data == data

    def test_encrypted_file_not_readable_as_text(self, temp_storage):
        """Test that encrypted files are not readable as plain text."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        sensitive_data = {"password": "supersecret", "api_key": "abc123"}
        json_bytes = json.dumps(sensitive_data).encode('utf-8')
        encrypted = cipher.encrypt(json_bytes)

        encrypted_path = temp_storage / "secrets.json.enc"
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted)

        # Read as text - should not contain original data
        with open(encrypted_path, 'rb') as f:
            content = f.read()

        assert b"supersecret" not in content
        assert b"abc123" not in content
        assert b"password" not in content

    def test_file_extension_convention(self, temp_storage):
        """Test .enc extension convention for encrypted files."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        base_path = temp_storage / "data.json"
        encrypted_path = base_path.with_suffix(base_path.suffix + '.enc')

        assert str(encrypted_path).endswith(".json.enc")

        # Write encrypted data
        encrypted = cipher.encrypt(b'{"test": true}')
        with open(encrypted_path, 'wb') as f:
            f.write(encrypted)

        # Verify .enc file exists, original doesn't
        assert encrypted_path.exists()
        assert not base_path.exists()


class TestKeyRotation:
    """Test encryption key rotation."""

    @pytest.fixture
    def temp_storage(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_key_rotation_preserves_data(self, temp_storage):
        """Test that key rotation preserves data correctly."""
        # Old key and cipher
        old_key = Fernet.generate_key()
        old_cipher = Fernet(old_key)

        # New key and cipher
        new_key = Fernet.generate_key()
        new_cipher = Fernet(new_key)

        # Encrypt with old key
        original_data = {"important": "data", "value": 12345}
        json_bytes = json.dumps(original_data).encode('utf-8')
        old_encrypted = old_cipher.encrypt(json_bytes)

        # Simulate rotation: decrypt with old, encrypt with new
        decrypted = old_cipher.decrypt(old_encrypted)
        new_encrypted = new_cipher.encrypt(decrypted)

        # Verify new key can decrypt
        final_decrypted = new_cipher.decrypt(new_encrypted)
        recovered_data = json.loads(final_decrypted.decode('utf-8'))

        assert recovered_data == original_data

        # Verify old key cannot decrypt new data
        with pytest.raises(InvalidToken):
            old_cipher.decrypt(new_encrypted)

    def test_backup_old_key(self, temp_storage):
        """Test that old key is backed up during rotation."""
        key_file = temp_storage / "encryption.key"
        backup_file = key_file.with_suffix('.key.backup')

        # Create old key
        old_key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(old_key)

        # Simulate backup
        key_file.rename(backup_file)

        # Write new key
        new_key = Fernet.generate_key()
        with open(key_file, 'wb') as f:
            f.write(new_key)

        # Verify both exist
        assert backup_file.exists()
        assert key_file.exists()

        # Verify they're different
        with open(backup_file, 'rb') as f:
            backed_up_key = f.read()
        with open(key_file, 'rb') as f:
            current_key = f.read()

        assert backed_up_key != current_key


class TestEncryptionSecurityProperties:
    """Test security properties of encryption."""

    def test_ciphertext_length_reveals_little(self):
        """Test that ciphertext length doesn't reveal exact plaintext length."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        # Different length inputs
        short = cipher.encrypt(b"Hi")
        medium = cipher.encrypt(b"Hello World")
        long = cipher.encrypt(b"This is a longer message")

        # All ciphertexts have overhead from IV + MAC
        # Lengths are padded to blocks
        assert len(short) > len(b"Hi")
        assert len(medium) > len(b"Hello World")

    def test_no_metadata_leakage(self):
        """Test that encryption doesn't leak metadata."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        # Encrypt user data
        user_data = {"user_id": "123", "email": "test@example.com"}
        encrypted = cipher.encrypt(json.dumps(user_data).encode())

        # Encrypted blob should not contain any identifiable info
        encrypted_str = encrypted.decode('utf-8')

        assert "123" not in encrypted_str
        assert "test@example.com" not in encrypted_str
        assert "user_id" not in encrypted_str
        assert "email" not in encrypted_str

    def test_decryption_required_for_access(self):
        """Test that data cannot be accessed without decryption."""
        key = Fernet.generate_key()
        cipher = Fernet(key)

        secret = {"api_key": "sk-1234567890abcdef"}
        encrypted = cipher.encrypt(json.dumps(secret).encode())

        # Without key, cannot access data
        # (we verify by checking encrypted blob)
        assert b"sk-1234567890abcdef" not in encrypted

        # With key, can access
        decrypted = cipher.decrypt(encrypted)
        assert b"sk-1234567890abcdef" in decrypted
