"""PII (Personally Identifiable Information) masking utilities."""

import hashlib
from typing import Optional


def mask_text(text: str, show_chars: int = 3) -> str:
    """
    Mask text showing only first few characters.

    Args:
        text: Text to mask
        show_chars: Number of characters to show at the beginning

    Returns:
        Masked text (e.g., "Hel***")

    Examples:
        >>> mask_text("Hello World", 3)
        'Hel***'
        >>> mask_text("ab", 3)
        'ab'
        >>> mask_text("", 3)
        ''
    """
    if not text:
        return ""

    if len(text) <= show_chars:
        return text

    return text[:show_chars] + "*" * min(len(text) - show_chars, 10)


def hash_user_id(user_id: str) -> str:
    """
    Hash user ID for logging purposes.

    Args:
        user_id: User ID to hash

    Returns:
        First 8 characters of SHA-256 hash

    Examples:
        >>> len(hash_user_id("123456"))
        8
        >>> hash_user_id("123") == hash_user_id("123")
        True
    """
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]


def mask_email(email: str) -> str:
    """
    Mask email address.

    Args:
        email: Email to mask

    Returns:
        Masked email (e.g., "joh***@exa***.com")

    Examples:
        >>> mask_email("john.doe@example.com")
        'joh***@exa***.com'
        >>> mask_email("a@b.c")
        'a@b.c'
    """
    if "@" not in email:
        return mask_text(email)

    local, domain = email.split("@", 1)
    domain_parts = domain.split(".", 1)

    masked_local = mask_text(local, 3)

    if len(domain_parts) > 1:
        masked_domain = mask_text(domain_parts[0], 3) + "." + domain_parts[1]
    else:
        masked_domain = mask_text(domain_parts[0], 3)

    return f"{masked_local}@{masked_domain}"


def mask_phone(phone: str) -> str:
    """
    Mask phone number.

    Args:
        phone: Phone number to mask

    Returns:
        Masked phone (e.g., "+7***456")

    Examples:
        >>> mask_phone("+79991234567")
        '+7***567'
        >>> mask_phone("123")
        '123'
    """
    if len(phone) <= 6:
        return phone

    return phone[:2] + "***" + phone[-3:]


def sanitize_for_logging(text: Optional[str], max_length: int = 50) -> str:
    """
    Sanitize text for safe logging.

    - Masks long text
    - Removes newlines
    - Truncates to max length

    Args:
        text: Text to sanitize
        max_length: Maximum length of returned text

    Returns:
        Sanitized text safe for logging

    Examples:
        >>> sanitize_for_logging("Hello World", 20)
        'Hel***'
        >>> sanitize_for_logging("Short", 20)
        'Sho***'
        >>> sanitize_for_logging(None)
        ''
    """
    if not text:
        return ""

    # Remove newlines and extra spaces
    cleaned = " ".join(text.split())

    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length] + "..."

    # Mask
    return mask_text(cleaned, 3)


def safe_log_params(**kwargs) -> dict:
    """
    Create safe logging parameters with PII masking.

    Automatically masks common PII fields:
    - user_id → hashed
    - title, text, details → masked
    - email → masked
    - phone → masked

    Args:
        **kwargs: Arbitrary keyword arguments

    Returns:
        Dictionary with masked values safe for logging

    Examples:
        >>> params = safe_log_params(user_id="12345", title="Meeting with John", email="test@example.com")
        >>> 'user_id_hash' in params
        True
        >>> 'title_masked' in params
        True
    """
    result = {}

    for key, value in kwargs.items():
        if value is None:
            result[key] = None
            continue

        # Hash user IDs
        if key in ["user_id", "chat_id"]:
            result[f"{key}_hash"] = hash_user_id(str(value))

        # Mask text fields
        elif key in ["title", "text", "details", "message", "description", "summary"]:
            result[f"{key}_masked"] = sanitize_for_logging(str(value))

        # Mask emails
        elif key in ["email", "attendee"]:
            result[f"{key}_masked"] = mask_email(str(value))

        # Mask phones
        elif key in ["phone", "phone_number"]:
            result[f"{key}_masked"] = mask_phone(str(value))

        # Keep other fields as-is
        else:
            result[key] = value

    return result
