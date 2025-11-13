#!/usr/bin/env python3
"""
Script to automatically create Radicale users file with correct MD5 format
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def setup_radicale_users():
    """Create Radicale users file with correct MD5 hash format."""
    
    # Path to users file
    users_file = Path("../radicale_config/users")
    
    # Create directory if not exists
    users_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"📁 Creating Radicale users file at: {users_file}")
    
    # Get credentials from environment with fallbacks
    bot_user = os.getenv("RADICALE_BOT_USER")
    bot_password_hash = os.getenv("RADICALE_BOT_PASSWORD")
    admin_user = os.getenv("RADICALE_ADMIN_USER")
    admin_password_hash = os.getenv("RADICALE_ADMIN_PASSWORD")
    
    print(f"🔑 Bot user: {bot_user}")
    print(f"🔑 Admin user: {admin_user}")
    
    # Format MD5 hashes correctly for htpasswd
    # Radicale expects: $apr1$SALT$HASH
    def format_md5_hash(password_hash):
        """
        Convert plain hash to correct htpasswd MD5 format.
        Format: $apr1$SALT$HASH (8 chars salt + 22 chars hash)
        """
        if not password_hash:
            return ""
        
        if password_hash.startswith('$apr1$') and password_hash.count('$') == 2:
            return password_hash
        
        if len(password_hash) >= 30:
            salt = password_hash[:8]
            hash_part = password_hash[8:]
            return f'$apr1${salt}${hash_part}'
        else:
            print(f"⚠️  Warning: Invalid hash length for {password_hash}")
            return f'$apr1${password_hash}'
    
    # Format the passwords
    formatted_bot_hash = format_md5_hash(bot_password_hash)
    formatted_admin_hash = format_md5_hash(admin_password_hash)
    
    print(f"🔒 Formatted bot hash: {formatted_bot_hash}")
    print(f"🔒 Formatted admin hash: {formatted_admin_hash}")
    
    # Create users file content
    users_content = f"""{bot_user}:{formatted_bot_hash}
{admin_user}:{formatted_admin_hash}
"""
    
    # Write to file
    users_file.write_text(users_content, encoding='utf-8')
    print(f"✅ Radicale users file created successfully!")
    print(f"   📍 Location: {users_file}")
    print(f"   👤 Users: {bot_user}, {admin_user}")
    
    # Verify file was created
    if users_file.exists():
        file_size = users_file.stat().st_size
        print(f"✅ Verification: File exists ({file_size} bytes)")
        
        # Show file content for verification
        content = users_file.read_text(encoding='utf-8')
        print("📄 File content:")
        print(content)
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