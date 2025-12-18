"""Test user detection utility.

Centralized configuration for identifying test accounts
to prevent them from polluting production analytics.
"""

import os
import re
from typing import Optional

# Test user ID patterns (exact matches)
TEST_USER_IDS = {
    # From pytest fixtures
    "123456789",              # conftest.py sample_user_id
    "test_user_12345",        # test_calendar_service.py
    "property_test_user_123", # test_property_service.py
    # Mock users from generate_mock_data.py
    "1234567",
    "2345678",
    "3456789",
    "4567890",
    "5678901",
    "6789012",
    "7890123",
}

# Test username patterns (exact matches and regex)
TEST_USERNAME_PATTERNS = [
    # Exact matches
    "aibroker_bot",           # Test bot account
    # Regex patterns
    r"^test_user.*",          # test_user*
    r".*_test_.*",            # *_test_*
    r"^property_test.*",      # property_test*
]

# Compile regex patterns once for performance
_COMPILED_PATTERNS = [re.compile(pattern) for pattern in TEST_USERNAME_PATTERNS]


def is_test_user(user_id: str, username: Optional[str] = None) -> bool:
    """
    Check if user is a test account.
    
    Args:
        user_id: Telegram user ID
        username: Telegram username (without @)
    
    Returns:
        True if user is a test account, False otherwise
    
    Examples:
        >>> is_test_user("123456789")
        True
        >>> is_test_user("real_user_id")
        False
        >>> is_test_user("12345", "test_user_abc")
        True
        >>> is_test_user("12345", "aibroker_bot")
        True
    """
    # Check if running in pytest
    if os.environ.get('PYTEST_RUNNING') == '1':
        return True
    
    # Check exact user_id match
    if user_id in TEST_USER_IDS:
        return True
    
    # Check username patterns
    if username:
        # Exact match
        if username in TEST_USERNAME_PATTERNS:
            return True
        
        # Regex match
        for pattern in _COMPILED_PATTERNS:
            if pattern.match(username):
                return True
    
    return False


def mark_test_data_in_db():
    """
    One-time utility to mark existing test data in database.
    
    Should be run once after deployment to clean up existing analytics.
    """
    from app.services.analytics_service import analytics_service
    
    conn = analytics_service._get_connection()
    try:
        # Mark actions with test user IDs
        placeholders = ','.join('?' * len(TEST_USER_IDS))
        cursor = conn.execute(f'''
            UPDATE actions SET is_test = 1
            WHERE user_id IN ({placeholders}) AND is_test = 0
        ''', tuple(TEST_USER_IDS))
        
        marked_by_id = cursor.rowcount
        
        # Mark actions with test usernames (requires join with users table)
        # Build username conditions
        username_conditions = []
        for username in TEST_USERNAME_PATTERNS:
            if not username.startswith('^') and not '.*' in username:
                # Exact match
                username_conditions.append(f"u.username = '{username}'")
            else:
                # Regex match - use LIKE for basic patterns
                like_pattern = username.replace('^', '').replace('.*', '%').replace(r'\.*', '%')
                username_conditions.append(f"u.username LIKE '{like_pattern}'")
        
        if username_conditions:
            username_where = ' OR '.join(username_conditions)
            cursor = conn.execute(f'''
                UPDATE actions SET is_test = 1
                WHERE user_id IN (
                    SELECT user_id FROM users u WHERE {username_where}
                ) AND is_test = 0
            ''')
            
            marked_by_username = cursor.rowcount
        else:
            marked_by_username = 0
        
        conn.commit()
        
        total_marked = marked_by_id + marked_by_username
        return {
            'marked_by_id': marked_by_id,
            'marked_by_username': marked_by_username,
            'total_marked': total_marked
        }
    finally:
        conn.close()

