#!/bin/bash

# ========================================
# Production Deployment Script
# AI Calendar Assistant with SMS Auth
# ========================================

set -e

echo "🚀 Starting production deployment..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "ℹ️  $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then 
    print_error "Do not run as root! Run as regular user with sudo access."
    exit 1
fi

# 1. Check .env file
print_info "Checking .env configuration..."

if [ ! -f .env ]; then
    print_error ".env file not found!"
    print_info "Creating from template..."
    cp env.sms_production.example .env
    print_warning "Please edit .env file with your settings and run again!"
    exit 1
fi

# Check required variables
required_vars=("SECRET_KEY" "SMS_PROVIDER" "SMS_RU_API_ID" "TELEGRAM_BOT_TOKEN")
missing_vars=()

for var in "${required_vars[@]}"; do
    if ! grep -q "^${var}=.\+" .env; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required variables in .env:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

# Check if using default SECRET_KEY
if grep -q "SECRET_KEY=ЗАМЕНИТЕ" .env; then
    print_error "Please generate and set SECRET_KEY in .env!"
    print_info "Run: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
    exit 1
fi

# Check APP_ENV
if ! grep -q "^APP_ENV=production" .env; then
    print_warning "APP_ENV is not set to 'production'!"
    read -p "Continue anyway? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_success ".env configuration OK"
echo ""

# 2. Check Docker
print_info "Checking Docker..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed!"
    print_info "Install with: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed!"
    exit 1
fi

print_success "Docker OK"
echo ""

# 3. Check SMS.ru balance
print_info "Checking SMS.ru balance..."

SMS_API_ID=$(grep "^SMS_RU_API_ID=" .env | cut -d'=' -f2)

if [ -n "$SMS_API_ID" ]; then
    balance_response=$(curl -s "https://sms.ru/my/balance?api_id=$SMS_API_ID")
    
    if echo "$balance_response" | grep -q "balance"; then
        balance=$(echo "$balance_response" | grep -oP '(?<="balance":)[0-9.]+')
        print_success "SMS.ru balance: ${balance}₽"
        
        if (( $(echo "$balance < 10" | bc -l) )); then
            print_warning "Low balance! Please top up at https://sms.ru/"
        fi
    else
        print_warning "Could not check SMS.ru balance"
    fi
else
    print_warning "SMS_RU_API_ID not set"
fi

echo ""

# 4. Create data directory
print_info "Creating data directory..."
mkdir -p data
chmod 700 data
print_success "Data directory OK"
echo ""

# 5. Pull latest images
print_info "Pulling Docker images..."
docker-compose pull
print_success "Images pulled"
echo ""

# 6. Build application
print_info "Building application..."
docker-compose build --no-cache
print_success "Build complete"
echo ""

# 7. Stop old containers
print_info "Stopping old containers..."
docker-compose down
print_success "Stopped"
echo ""

# 8. Start application
print_info "Starting application..."
docker-compose up -d
print_success "Application started"
echo ""

# 9. Wait for application to start
print_info "Waiting for application to start..."
sleep 5

# 10. Check health
print_info "Checking health..."

health_check=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health || echo "000")

if [ "$health_check" == "200" ]; then
    print_success "Health check OK"
else
    print_error "Health check failed (HTTP $health_check)"
    print_info "Checking logs..."
    docker-compose logs --tail=50
    exit 1
fi

echo ""

# 11. Show logs
print_info "Recent logs:"
docker-compose logs --tail=20
echo ""

# 12. Final checks
print_success "Deployment complete! 🎉"
echo ""
echo "=================================="
echo "📋 NEXT STEPS:"
echo "=================================="
echo ""
echo "1. Check logs:"
echo "   docker-compose logs -f"
echo ""
echo "2. Test SMS authentication:"
echo "   curl -X POST http://localhost:8000/api/auth/sms/request \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"phone\": \"+79991234567\"}'"
echo ""
echo "3. Open demo page:"
echo "   http://your-domain.com/static/sms_auth_demo.html"
echo ""
echo "4. Configure Nginx + SSL:"
echo "   See: PRODUCTION_DEPLOYMENT.md"
echo ""
echo "=================================="
echo "📊 STATUS:"
echo "=================================="
echo ""

# Show running containers
docker-compose ps

echo ""
print_success "All systems operational! 🚀"
