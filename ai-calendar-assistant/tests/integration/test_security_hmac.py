"""Tests for Telegram WebApp HMAC authentication."""

import pytest
import hmac
import hashlib
import json
from urllib.parse import urlencode
from unittest.mock import patch, MagicMock

from app.middleware.telegram_auth import (
    validate_telegram_init_data,
    extract_user_info_from_init_data,
    extract_user_id_from_init_data,
)


class TestTelegramHMACValidation:
    """Test Telegram initData HMAC signature validation."""

    @pytest.fixture
    def bot_token(self):
        """Test bot token."""
        return "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

    @pytest.fixture
    def valid_user_data(self):
        """Valid user JSON data."""
        return {
            "id": 123456789,
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "language_code": "en"
        }

    def _create_init_data(self, bot_token: str, user_data: dict, extra_params: dict = None) -> str:
        """
        Create valid Telegram initData string with correct HMAC signature.

        This mimics how Telegram creates the initData.
        """
        # Build params
        params = {
            "user": json.dumps(user_data),
            "auth_date": "1704067200",
            "query_id": "AAGxyz123"
        }
        if extra_params:
            params.update(extra_params)

        # Create data check string (alphabetically sorted)
        data_check_arr = [f"{k}={v}" for k, v in sorted(params.items())]
        data_check_string = '\n'.join(data_check_arr)

        # Create secret key
        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        # Calculate hash
        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        # Add hash to params
        params["hash"] = calculated_hash

        return urlencode(params)

    # ==================== Valid Signatures ====================

    def test_valid_signature(self, bot_token, valid_user_data):
        """Test that valid HMAC signature is accepted."""
        init_data = self._create_init_data(bot_token, valid_user_data)

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is not None
        assert "user" in result
        assert "auth_date" in result

    def test_valid_signature_with_extra_params(self, bot_token, valid_user_data):
        """Test valid signature with additional parameters."""
        extra_params = {
            "start_param": "my_start_param",
            "chat_type": "private"
        }
        init_data = self._create_init_data(bot_token, valid_user_data, extra_params)

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is not None
        assert result.get("start_param") == "my_start_param"

    # ==================== Invalid Signatures ====================

    def test_invalid_hash(self, bot_token, valid_user_data):
        """Test that invalid hash is rejected."""
        init_data = self._create_init_data(bot_token, valid_user_data)
        # Corrupt the hash
        init_data = init_data.replace(init_data[-10:], "corrupted!")

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is None

    def test_wrong_bot_token(self, bot_token, valid_user_data):
        """Test that signature with wrong bot token is rejected."""
        init_data = self._create_init_data(bot_token, valid_user_data)

        # Validate with different token
        result = validate_telegram_init_data(init_data, "9999999999:WrongToken")

        assert result is None

    def test_missing_hash(self, bot_token, valid_user_data):
        """Test that initData without hash is rejected."""
        params = {
            "user": json.dumps(valid_user_data),
            "auth_date": "1704067200"
        }
        init_data = urlencode(params)

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is None

    def test_tampered_data(self, bot_token, valid_user_data):
        """Test that tampered data is rejected."""
        init_data = self._create_init_data(bot_token, valid_user_data)

        # Tamper with user data by modifying part of the string
        init_data = init_data.replace("testuser", "hackeduser")

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is None

    def test_empty_init_data(self, bot_token):
        """Test that empty initData is rejected."""
        result = validate_telegram_init_data("", bot_token)
        assert result is None

    def test_malformed_init_data(self, bot_token):
        """Test that malformed initData is rejected."""
        result = validate_telegram_init_data("not_valid_query_string", bot_token)
        assert result is None


class TestUserInfoExtraction:
    """Test user info extraction from validated initData."""

    def test_extract_user_info_valid(self):
        """Test extracting user info from valid data."""
        validated_data = {
            "user": json.dumps({
                "id": 123456789,
                "first_name": "Test",
                "last_name": "User",
                "username": "testuser"
            }),
            "auth_date": "1704067200"
        }

        user_info = extract_user_info_from_init_data(validated_data)

        assert user_info is not None
        assert user_info["user_id"] == "123456789"
        assert user_info["first_name"] == "Test"
        assert user_info["last_name"] == "User"
        assert user_info["username"] == "testuser"

    def test_extract_user_info_minimal(self):
        """Test extracting user info with minimal fields."""
        validated_data = {
            "user": json.dumps({
                "id": 123456789,
                "first_name": "Test"
            }),
            "auth_date": "1704067200"
        }

        user_info = extract_user_info_from_init_data(validated_data)

        assert user_info is not None
        assert user_info["user_id"] == "123456789"
        assert user_info["first_name"] == "Test"
        assert user_info["username"] is None
        assert user_info["last_name"] is None

    def test_extract_user_info_no_user_field(self):
        """Test extraction when user field is missing."""
        validated_data = {
            "auth_date": "1704067200"
        }

        user_info = extract_user_info_from_init_data(validated_data)

        assert user_info is None

    def test_extract_user_info_invalid_json(self):
        """Test extraction with invalid JSON in user field."""
        validated_data = {
            "user": "not valid json",
            "auth_date": "1704067200"
        }

        user_info = extract_user_info_from_init_data(validated_data)

        assert user_info is None

    def test_extract_user_info_no_id(self):
        """Test extraction when user has no id field."""
        validated_data = {
            "user": json.dumps({
                "first_name": "Test",
                "username": "testuser"
            }),
            "auth_date": "1704067200"
        }

        user_info = extract_user_info_from_init_data(validated_data)

        assert user_info is None


class TestUserIdExtraction:
    """Test backward-compatible user_id extraction."""

    def test_extract_user_id_valid(self):
        """Test extracting just user_id."""
        validated_data = {
            "user": json.dumps({
                "id": 987654321,
                "first_name": "Test"
            }),
            "auth_date": "1704067200"
        }

        user_id = extract_user_id_from_init_data(validated_data)

        assert user_id == "987654321"

    def test_extract_user_id_no_user(self):
        """Test extraction returns None when no user."""
        validated_data = {
            "auth_date": "1704067200"
        }

        user_id = extract_user_id_from_init_data(validated_data)

        assert user_id is None


class TestHMACSecurityEdgeCases:
    """Test security edge cases for HMAC validation."""

    @pytest.fixture
    def bot_token(self):
        return "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"

    def test_replay_attack_protection(self, bot_token):
        """
        Test that old signatures can still validate.

        Note: Actual replay protection should check auth_date
        and reject requests older than X seconds.
        """
        user_data = {"id": 123, "first_name": "Test"}
        params = {
            "user": json.dumps(user_data),
            "auth_date": "1609459200"  # Old date (2021-01-01)
        }

        # Create valid signature
        data_check_arr = [f"{k}={v}" for k, v in sorted(params.items())]
        data_check_string = '\n'.join(data_check_arr)

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        params["hash"] = calculated_hash
        init_data = urlencode(params)

        # Signature is valid (replay protection should be at application level)
        result = validate_telegram_init_data(init_data, bot_token)
        assert result is not None

    def test_unicode_in_user_data(self, bot_token):
        """Test HMAC validation with unicode characters."""
        user_data = {
            "id": 123456789,
            "first_name": "Тест",  # Russian
            "last_name": "Юзер"
        }

        params = {
            "user": json.dumps(user_data, ensure_ascii=False),
            "auth_date": "1704067200"
        }

        data_check_arr = [f"{k}={v}" for k, v in sorted(params.items())]
        data_check_string = '\n'.join(data_check_arr)

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        params["hash"] = calculated_hash
        init_data = urlencode(params)

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is not None
        user_info = extract_user_info_from_init_data(result)
        assert user_info["first_name"] == "Тест"

    def test_special_characters_in_params(self, bot_token):
        """Test HMAC validation with special characters."""
        user_data = {
            "id": 123456789,
            "first_name": "Test&User",
            "username": "test=user"
        }

        params = {
            "user": json.dumps(user_data),
            "auth_date": "1704067200",
            "start_param": "ref=123&campaign=test"
        }

        data_check_arr = [f"{k}={v}" for k, v in sorted(params.items())]
        data_check_string = '\n'.join(data_check_arr)

        secret_key = hmac.new(
            b"WebAppData",
            bot_token.encode(),
            hashlib.sha256
        ).digest()

        calculated_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        params["hash"] = calculated_hash
        init_data = urlencode(params)

        result = validate_telegram_init_data(init_data, bot_token)

        assert result is not None
