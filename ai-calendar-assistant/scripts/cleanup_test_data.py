#!/usr/bin/env python3
"""
One-time cleanup script to mark existing test data in production database.

This script identifies and marks test user data based on:
- Known test user IDs from pytest fixtures
- Test username patterns
- Mock user IDs from generate_mock_data.py

Usage:
    python scripts/cleanup_test_data.py [--dry-run]

Options:
    --dry-run    Show what would be marked without making changes
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.test_detection import mark_test_data_in_db, TEST_USER_IDS, TEST_USERNAME_PATTERNS
from app.services.analytics_service import analytics_service


def show_current_stats():
    """Show current database statistics."""
    conn = analytics_service._get_connection()
    try:
        # Total actions
        total = conn.execute('SELECT COUNT(*) FROM actions').fetchone()[0]
        
        # Test actions
        test = conn.execute('SELECT COUNT(*) FROM actions WHERE is_test = 1').fetchone()[0]
        
        # Production actions
        prod = conn.execute('SELECT COUNT(*) FROM actions WHERE is_test = 0').fetchone()[0]
        
        # Test users
        test_users = conn.execute(
            'SELECT COUNT(DISTINCT user_id) FROM actions WHERE is_test = 1'
        ).fetchone()[0]
        
        # Production users
        prod_users = conn.execute(
            'SELECT COUNT(DISTINCT user_id) FROM actions WHERE is_test = 0'
        ).fetchone()[0]
        
        print("\n📊 Current Database Statistics:")
        print(f"  Total actions:      {total:,}")
        print(f"  Test actions:       {test:,} ({test/total*100:.1f}%)" if total > 0 else "  Test actions:       0")
        print(f"  Production actions: {prod:,} ({prod/total*100:.1f}%)" if total > 0 else "  Production actions: 0")
        print(f"  Test users:         {test_users}")
        print(f"  Production users:   {prod_users}")
        
        return {
            'total': total,
            'test': test,
            'prod': prod,
            'test_users': test_users,
            'prod_users': prod_users
        }
    finally:
        conn.close()


def preview_affected_data():
    """Show what data would be affected."""
    conn = analytics_service._get_connection()
    try:
        print("\n🔍 Preview of data to be marked as test:")
        print("\n1️⃣  Test User IDs:")
        for user_id in sorted(TEST_USER_IDS):
            count = conn.execute(
                'SELECT COUNT(*) FROM actions WHERE user_id = ? AND is_test = 0',
                (user_id,)
            ).fetchone()[0]
            if count > 0:
                print(f"  {user_id}: {count} actions")
        
        print("\n2️⃣  Test Username Patterns:")
        for pattern in TEST_USERNAME_PATTERNS:
            # Simple LIKE conversion for preview
            like_pattern = pattern.replace('^', '').replace('.*', '%').replace(r'\.*', '%')
            if not pattern.startswith('^') and not '.*' in pattern:
                # Exact match
                count = conn.execute('''
                    SELECT COUNT(*) FROM actions a
                    JOIN users u ON a.user_id = u.user_id
                    WHERE u.username = ? AND a.is_test = 0
                ''', (pattern,)).fetchone()[0]
            else:
                # Pattern match
                count = conn.execute(f'''
                    SELECT COUNT(*) FROM actions a
                    JOIN users u ON a.user_id = u.user_id
                    WHERE u.username LIKE ? AND a.is_test = 0
                ''', (like_pattern,)).fetchone()[0]
            
            if count > 0:
                print(f"  {pattern}: {count} actions")
    finally:
        conn.close()


def main():
    """Main cleanup function."""
    parser = argparse.ArgumentParser(description='Cleanup test data from analytics database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    args = parser.parse_args()
    
    print("🧹 Test Data Cleanup Script")
    print("=" * 60)
    
    # Show current stats
    stats_before = show_current_stats()
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
        preview_affected_data()
        print("\n✅ Dry run complete. Run without --dry-run to apply changes.")
        return
    
    # Confirm before proceeding
    preview_affected_data()
    print("\n⚠️  This will mark the above data as test data.")
    response = input("Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("❌ Cancelled.")
        return
    
    # Perform cleanup
    print("\n🔄 Marking test data...")
    result = mark_test_data_in_db()
    
    print(f"\n✅ Cleanup complete!")
    print(f"  Marked by user_id:  {result['marked_by_id']:,} actions")
    print(f"  Marked by username: {result['marked_by_username']:,} actions")
    print(f"  Total marked:       {result['total_marked']:,} actions")
    
    # Show updated stats
    print("\n" + "=" * 60)
    stats_after = show_current_stats()
    
    # Show difference
    print("\n📈 Changes:")
    print(f"  Test actions:   {stats_before['test']:,} → {stats_after['test']:,} (+{stats_after['test'] - stats_before['test']:,})")
    print(f"  Prod actions:   {stats_before['prod']:,} → {stats_after['prod']:,} ({stats_after['prod'] - stats_before['prod']:+,})")
    print(f"  Test users:     {stats_before['test_users']} → {stats_after['test_users']} (+{stats_after['test_users'] - stats_before['test_users']})")
    print(f"  Prod users:     {stats_before['prod_users']} → {stats_after['prod_users']} ({stats_after['prod_users'] - stats_before['prod_users']:+})")
    
    print("\n🎉 All done! Test data has been marked and will be excluded from analytics.")


if __name__ == "__main__":
    main()

