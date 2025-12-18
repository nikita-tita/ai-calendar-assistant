#!/usr/bin/env python3
"""
Migration script: Admin system v1 (3 passwords) → v2 (login/password + 2FA)

This script:
1. Creates admin_users table
2. Creates first admin user from ADMIN_PASSWORD_1
3. Migrates panic mode (PASSWORD_2+3 → panic_password)
4. Creates audit log table
5. Backs up old configuration

Usage:
    python scripts/migrate_admin_to_v2.py [--dry-run] [--db-path=analytics.db]
"""

import os
import sys
import argparse
import sqlite3
import bcrypt
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def hash_password(password: str) -> str:
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def create_tables(conn: sqlite3.Connection):
    """Create admin_users and admin_audit_log tables."""
    print("📋 Creating tables...")
    
    # Admin users table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE,
            password_hash TEXT NOT NULL,
            totp_secret TEXT,
            totp_enabled INTEGER DEFAULT 0,
            panic_password_hash TEXT,
            role TEXT DEFAULT 'admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP,
            last_login_ip TEXT,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # Admin audit log table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS admin_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_user_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            action_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            success INTEGER DEFAULT 1,
            FOREIGN KEY (admin_user_id) REFERENCES admin_users(id)
        )
    ''')
    
    conn.commit()
    print("✅ Tables created")


def migrate_admin_user(conn: sqlite3.Connection, dry_run: bool = False):
    """Migrate from 3-password system to login/password system."""
    print("\n🔐 Migrating admin user...")
    
    # Get passwords from environment
    password1 = os.getenv("ADMIN_PASSWORD_1") or os.getenv("ADMIN_PRIMARY_PASSWORD")
    password2 = os.getenv("ADMIN_PASSWORD_2") or os.getenv("ADMIN_SECONDARY_PASSWORD")
    password3 = os.getenv("ADMIN_PASSWORD_3") or os.getenv("ADMIN_TERTIARY_PASSWORD")
    admin_email = os.getenv("ADMIN_EMAIL", "nikitatitov070@yandex.ru")
    
    if not password1:
        print("❌ ERROR: ADMIN_PASSWORD_1 not found in environment")
        print("   Set it in .env file and try again")
        return False
    
    # Check if admin already exists
    cursor = conn.execute('SELECT COUNT(*) FROM admin_users WHERE username = ?', ('admin',))
    exists = cursor.fetchone()[0] > 0
    
    if exists:
        print("⚠️  Admin user 'admin' already exists")
        cursor = conn.execute('SELECT * FROM admin_users WHERE username = ?', ('admin',))
        user = cursor.fetchone()
        print(f"   Username: admin")
        print(f"   Email: {user[2]}")
        print(f"   Role: {user[7]}")
        print(f"   2FA: {'Enabled' if user[5] else 'Disabled'}")
        print(f"   Created: {user[8]}")
        return True
    
    print(f"\n📝 Creating admin user:")
    print(f"   Username: admin")
    print(f"   Email: {admin_email}")
    print(f"   Role: admin")
    print(f"   Password: from ADMIN_PASSWORD_1")
    
    # Create panic password (fake mode) from PASSWORD_2
    panic_password = None
    if password2:
        print(f"   Panic mode: Enabled (from ADMIN_PASSWORD_2)")
        print(f"      • Real password (PASSWORD_1) → normal admin access")
        print(f"      • Panic password (PASSWORD_2) → fake mode (empty data)")
        panic_password = password2
    else:
        print(f"   Panic mode: Disabled (no ADMIN_PASSWORD_2)")
    
    if dry_run:
        print("\n🔍 DRY RUN - No changes made")
        return True
    
    # Hash passwords
    password_hash = hash_password(password1)
    panic_hash = hash_password(panic_password) if panic_password else None
    
    # Insert admin user
    conn.execute('''
        INSERT INTO admin_users
        (username, email, password_hash, panic_password_hash, role, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('admin', admin_email, password_hash, panic_hash, 'admin', datetime.now().isoformat()))
    
    conn.commit()
    
    print("\n✅ Admin user created successfully!")
    print("\n📋 Next steps:")
    print("   1. Open admin panel: http://your-domain/static/admin.html")
    print("   2. Login:")
    print("      Username: admin")
    print(f"      Password: <your ADMIN_PASSWORD_1>")
    print("   3. Setup 2FA (Google Authenticator)")
    print("   4. Update your .env file (remove old passwords)")
    print("\n⚠️  IMPORTANT: Save your ADMIN_PASSWORD_1 - it's your new admin password!")
    
    return True


def create_backup(db_path: str):
    """Create backup of current database."""
    if not os.path.exists(db_path):
        print(f"ℹ️  Database {db_path} doesn't exist yet")
        return
    
    backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    import shutil
    shutil.copy2(db_path, backup_path)
    
    print(f"✅ Backup created: {backup_path}")


def verify_migration(conn: sqlite3.Connection):
    """Verify migration completed successfully."""
    print("\n🔍 Verifying migration...")
    
    # Check tables exist
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name IN ('admin_users', 'admin_audit_log')"
    )
    tables = [row[0] for row in cursor.fetchall()]
    
    if 'admin_users' not in tables:
        print("❌ admin_users table not found")
        return False
    
    if 'admin_audit_log' not in tables:
        print("❌ admin_audit_log table not found")
        return False
    
    # Check admin user exists
    cursor = conn.execute('SELECT COUNT(*) FROM admin_users WHERE username = ?', ('admin',))
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        print("❌ Admin user not found")
        return False
    
    print("✅ Migration verified successfully")
    return True


def main():
    parser = argparse.ArgumentParser(description='Migrate admin system to v2')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--db-path',
        default='analytics.db',
        help='Path to database file (default: analytics.db)'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("🔄 Admin System Migration: v1 → v2")
    print("=" * 70)
    print()
    print("This will migrate from 3-password system to login/password + 2FA")
    
    if args.dry_run:
        print("\n🔍 DRY RUN MODE - No changes will be made")
    
    print(f"\nDatabase: {args.db_path}")
    
    # Create backup (unless dry run)
    if not args.dry_run:
        create_backup(args.db_path)
    
    # Connect to database
    conn = sqlite3.connect(args.db_path)
    
    try:
        # Create tables
        create_tables(conn)
        
        # Migrate admin user
        if not migrate_admin_user(conn, dry_run=args.dry_run):
            print("\n❌ Migration failed")
            return 1
        
        # Verify (unless dry run)
        if not args.dry_run:
            if not verify_migration(conn):
                print("\n❌ Verification failed")
                return 1
        
        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        
        if args.dry_run:
            print("\nℹ️  Run without --dry-run to apply changes")
        
        return 0
    
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        conn.close()


if __name__ == '__main__':
    sys.exit(main())

