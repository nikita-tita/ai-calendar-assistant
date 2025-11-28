#!/usr/bin/env python3
"""
Script to automatically create Radicale users file with correct bcrypt format
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import bcrypt

load_dotenv()

def setup_radicale_users():
    """Create Radicale users file with correct bcrypt hash format."""
    
    # Path to users file
    users_file = Path("../radicale_config/users")
    
    # Create directory if not exists
    users_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Creating Radicale users file at: {users_file}")
    
    # Get credentials from environment
    bot_user = os.getenv("RADICALE_BOT_USER")
    bot_password = os.getenv("RADICALE_BOT_PASSWORD")  # Plain password now
    admin_user = os.getenv("RADICALE_ADMIN_USER")
    admin_password = os.getenv("RADICALE_ADMIN_PASSWORD")  # Plain password now
    
    print(f"🔑 Bot user: {bot_user}")
    print(f"🔑 Admin user: {admin_user}")
    
    def hash_bcrypt(password):
        """Hash password using bcrypt."""
        if not password:
            return ""
        # Generate bcrypt hash
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        return hashed.decode('utf-8')
    
    # Hash the passwords
    hashed_bot_password = hash_bcrypt(bot_password)
    hashed_admin_password = hash_bcrypt(admin_password)
    
    print("🔒 Passwords hashed with bcrypt")
    
    # Create users file content
    users_content = f"""{bot_user}:{hashed_bot_password}
{admin_user}:{hashed_admin_password}
"""
    
    # Write to file
    users_file.write_text(users_content, encoding='utf-8')
    print(f"✅ Radicale users file created successfully!")
    print(f"   📍 Location: {users_file}")
    print(f"   👤 Users: {bot_user}, {admin_user}")
    print(f"   🔐 Encryption: bcrypt")
    
    # Verify file was created
    if users_file.exists():
        file_size = users_file.stat().st_size
        print(f"✅ Verification: File exists ({file_size} bytes)")
        return True
    else:
        print("❌ Verification: File was not created!")
        return False

if __name__ == "__main__":
    try:
        print("🚀 Starting Radicale users setup...")
        success = setup_radicale_users()
        if success:
            print("🎉 Setup completed successfully!")
            sys.exit(0)
        else:
            print("💥 Setup failed!")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)