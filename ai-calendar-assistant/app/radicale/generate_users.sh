#!/bin/bash

# Generate htpasswd file for Radicale authentication
# Usage: ./generate_users.sh

set -e

USERS_FILE="./radicale/users"
RIGHTS_FILE="./radicale/rights"

echo "Generating Radicale authentication files..."

# Install htpasswd if not available
if ! command -v htpasswd &> /dev/null; then
    echo "htpasswd not found. Installing apache2-utils..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install httpd
    else
        sudo apt-get install -y apache2-utils
    fi
fi

# Generate admin user
read -p "Enter admin username [admin]: " ADMIN_USER
ADMIN_USER=${ADMIN_USER:-admin}

read -sp "Enter admin password: " ADMIN_PASS
echo

if [ -z "$ADMIN_PASS" ]; then
    echo "Error: Password cannot be empty"
    exit 1
fi

# Create users file with bcrypt encryption
htpasswd -cbB "$USERS_FILE" "$ADMIN_USER" "$ADMIN_PASS"
echo "✓ Created admin user: $ADMIN_USER"

# Generate service account for bot
BOT_USER="calendar_bot"
BOT_PASS=$(openssl rand -base64 32)

htpasswd -bB "$USERS_FILE" "$BOT_USER" "$BOT_PASS"
echo "✓ Created service user: $BOT_USER"

# Save bot credentials to .env
if grep -q "RADICALE_BOT_USER=" .env 2>/dev/null; then
    sed -i.bak "s/RADICALE_BOT_USER=.*/RADICALE_BOT_USER=$BOT_USER/" .env
    sed -i.bak "s/RADICALE_BOT_PASSWORD=.*/RADICALE_BOT_PASSWORD=$BOT_PASS/" .env
else
    echo "" >> .env
    echo "# Radicale service account" >> .env
    echo "RADICALE_BOT_USER=$BOT_USER" >> .env
    echo "RADICALE_BOT_PASSWORD=$BOT_PASS" >> .env
fi

echo "✓ Saved bot credentials to .env"

# Create rights file
cat > "$RIGHTS_FILE" << EOF
# Radicale Access Rights
# Documentation: https://radicale.org/v3.html#documentation/authentication-and-rights

# Admin has full access
[admin]
user = $ADMIN_USER
collection = .*
permissions = rw

# Bot service account has full access
[bot]
user = $BOT_USER
collection = .*
permissions = rw

# Users can only access their own calendars
[owner]
user = .+
collection = ^%(login)s/.*$
permissions = rw
EOF

echo "✓ Created rights configuration"

echo ""
echo "==================================="
echo "Setup complete!"
echo "==================================="
echo "Admin user: $ADMIN_USER"
echo "Bot user: $BOT_USER"
echo ""
echo "IMPORTANT: Keep these credentials secure!"
echo "Bot password has been saved to .env file."
echo ""
echo "Next steps:"
echo "1. Start services: docker-compose -f docker-compose.secure.yml up -d"
echo "2. Check Radicale web UI: http://localhost:5232 (if port exposed)"
echo "3. Test authentication with your admin credentials"
echo ""
