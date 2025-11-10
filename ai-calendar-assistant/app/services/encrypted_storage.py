"""Encrypted storage service for sensitive JSON files."""

import os
import json
from pathlib import Path
from typing import Any, Dict
from cryptography.fernet import Fernet
import structlog

logger = structlog.get_logger()


class EncryptedStorage:
    """
    Service for storing and retrieving encrypted JSON data.

    Uses Fernet (symmetric encryption) for encrypting data at rest.
    The encryption key is generated once and stored securely.
    """

    def __init__(self, data_dir: str = "/var/lib/calendar-bot"):
        """
        Initialize encrypted storage.

        Args:
            data_dir: Directory to store encrypted files and encryption key
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.key_file = self.data_dir / ".encryption_key"
        self.cipher = self._init_cipher()

        logger.info("encrypted_storage_initialized", data_dir=str(self.data_dir))

    def _init_cipher(self) -> Fernet:
        """Initialize encryption cipher with key from file or generate new one."""
        if self.key_file.exists():
            # Load existing key
            with open(self.key_file, 'rb') as f:
                key = f.read()
            logger.info("encryption_key_loaded")
        else:
            # Generate new key
            key = Fernet.generate_key()

            # Save key with restricted permissions
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600)  # Read/write for owner only

            logger.info("encryption_key_generated", key_file=str(self.key_file))

        return Fernet(key)

    def save(self, data: Dict[str, Any], filename: str, encrypt: bool = True):
        """
        Save data to file (optionally encrypted).

        Args:
            data: Data to save (must be JSON-serializable)
            filename: Name of file to save to
            encrypt: Whether to encrypt the data (default: True)
        """
        file_path = self.data_dir / filename

        try:
            # Convert to JSON
            json_data = json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8')

            if encrypt:
                # Encrypt data
                encrypted_data = self.cipher.encrypt(json_data)

                # Save encrypted data with .enc extension
                encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')
                with open(encrypted_path, 'wb') as f:
                    f.write(encrypted_data)

                # Remove unencrypted version if exists
                if file_path.exists():
                    file_path.unlink()

                logger.info("data_saved_encrypted",
                           filename=filename,
                           size_bytes=len(encrypted_data))
            else:
                # Save unencrypted (backward compatibility)
                with open(file_path, 'wb') as f:
                    f.write(json_data)

                logger.info("data_saved_unencrypted",
                           filename=filename,
                           size_bytes=len(json_data))

        except Exception as e:
            logger.error("save_failed",
                        filename=filename,
                        error=str(e),
                        exc_info=True)
            raise

    def load(self, filename: str, default: Any = None) -> Dict[str, Any]:
        """
        Load data from file (handles both encrypted and unencrypted).

        Args:
            filename: Name of file to load from
            default: Default value if file doesn't exist

        Returns:
            Loaded data or default value
        """
        file_path = self.data_dir / filename
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')

        try:
            # Try encrypted file first
            if encrypted_path.exists():
                with open(encrypted_path, 'rb') as f:
                    encrypted_data = f.read()

                # Decrypt data
                decrypted_data = self.cipher.decrypt(encrypted_data)
                data = json.loads(decrypted_data.decode('utf-8'))

                logger.info("data_loaded_encrypted",
                           filename=filename,
                           size_bytes=len(encrypted_data))
                return data

            # Fallback to unencrypted file (backward compatibility)
            elif file_path.exists():
                with open(file_path, 'rb') as f:
                    json_data = f.read()

                data = json.loads(json_data.decode('utf-8'))

                logger.info("data_loaded_unencrypted",
                           filename=filename,
                           size_bytes=len(json_data))

                # Auto-migrate to encrypted format
                logger.info("auto_migrating_to_encrypted", filename=filename)
                self.save(data, filename, encrypt=True)

                return data

            else:
                # File doesn't exist
                logger.info("data_file_not_found",
                           filename=filename,
                           returning_default=True)
                return default if default is not None else {}

        except Exception as e:
            logger.error("load_failed",
                        filename=filename,
                        error=str(e),
                        exc_info=True)

            # Return default on error
            return default if default is not None else {}

    def exists(self, filename: str) -> bool:
        """
        Check if file exists (encrypted or unencrypted).

        Args:
            filename: Name of file to check

        Returns:
            True if file exists
        """
        file_path = self.data_dir / filename
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')

        return encrypted_path.exists() or file_path.exists()

    def delete(self, filename: str):
        """
        Delete file (both encrypted and unencrypted versions).

        Args:
            filename: Name of file to delete
        """
        file_path = self.data_dir / filename
        encrypted_path = file_path.with_suffix(file_path.suffix + '.enc')

        deleted = False

        if encrypted_path.exists():
            encrypted_path.unlink()
            deleted = True

        if file_path.exists():
            file_path.unlink()
            deleted = True

        if deleted:
            logger.info("data_deleted", filename=filename)
        else:
            logger.warning("data_delete_not_found", filename=filename)

    def rotate_key(self, new_data_dir: str = None):
        """
        Rotate encryption key and re-encrypt all data.

        WARNING: This is a destructive operation. Backup before running!

        Args:
            new_data_dir: New directory to move data to (optional)
        """
        logger.warning("key_rotation_started")

        # Load all data with old key
        all_data = {}
        for file_path in self.data_dir.glob("*.enc"):
            filename = file_path.stem  # Remove .enc extension
            all_data[filename] = self.load(filename)

        # Generate new key
        new_key = Fernet.generate_key()
        new_cipher = Fernet(new_key)

        # Save old key as backup
        backup_key_file = self.key_file.with_suffix('.key.backup')
        if self.key_file.exists():
            self.key_file.rename(backup_key_file)

        # Write new key
        with open(self.key_file, 'wb') as f:
            f.write(new_key)
        os.chmod(self.key_file, 0o600)

        # Update cipher
        self.cipher = new_cipher

        # Re-encrypt all data with new key
        for filename, data in all_data.items():
            self.save(data, filename, encrypt=True)

        logger.info("key_rotation_completed",
                   files_reencrypted=len(all_data),
                   backup_key=str(backup_key_file))


# Global instance
encrypted_storage = EncryptedStorage()
