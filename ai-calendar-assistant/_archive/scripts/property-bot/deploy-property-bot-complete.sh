#!/bin/bash

# Property Bot Complete Deployment Script
# Автоматическое развертывание Property Search Bot (Stage 1-3)

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_header() {
    echo -e "${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if required commands exist
check_requirements() {
    print_header "Checking Requirements"

    local missing_deps=0

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        missing_deps=1
    else
        print_success "Docker is installed"
    fi

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        missing_deps=1
    else
        print_success "Docker Compose is installed"
    fi

    if [ $missing_deps -eq 1 ]; then
        print_error "Please install missing dependencies first"
        exit 1
    fi

    echo ""
}

# Create .env file if it doesn't exist
create_env_file() {
    print_header "Environment Configuration"

    if [ -f .env.property ]; then
        print_warning ".env.property already exists"
        read -p "Overwrite? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "Using existing .env.property"
            return
        fi
    fi

    print_info "Creating .env.property file..."

    # Prompt for required variables
    read -p "Enter Database Password: " db_password
    read -p "Enter Yandex GPT API Key: " yandex_gpt_key
    read -p "Enter Yandex GPT Folder ID: " yandex_folder_id
    read -p "Enter Telegram Bot Token: " telegram_token

    # Optional variables
    read -p "Enter Yandex Maps API Key (optional, press Enter to skip): " yandex_maps_key
    read -p "Enter Yandex Vision API Key (optional, press Enter to skip): " yandex_vision_key

    # Create .env file
    cat > .env.property << EOF
# Property Bot Environment Configuration
# Generated: $(date)

# ============================================
# REQUIRED CONFIGURATION
# ============================================

# Database
DB_PASSWORD=${db_password}

# Yandex GPT (REQUIRED)
YANDEX_GPT_API_KEY=${yandex_gpt_key}
YANDEX_GPT_FOLDER_ID=${yandex_folder_id}

# Telegram Bot
TELEGRAM_BOT_TOKEN=${telegram_token}

# ============================================
# OPTIONAL CONFIGURATION
# ============================================

# Yandex APIs (Optional - graceful degradation)
YANDEX_MAPS_API_KEY=${yandex_maps_key}
YANDEX_VISION_API_KEY=${yandex_vision_key}

# Application Settings
LOG_LEVEL=INFO
DEBUG=false
ENVIRONMENT=production

# Feature Flags
ENABLE_POI_ENRICHMENT=true
ENABLE_ROUTE_ENRICHMENT=true
ENABLE_VISION_ENRICHMENT=true
ENABLE_PRICE_CONTEXT=true
ENABLE_DEVELOPER_REPUTATION=true

# Cache Settings (in days/hours)
POI_CACHE_TTL_DAYS=7
ROUTE_CACHE_TTL_DAYS=30
PRICE_CACHE_TTL_HOURS=24

# Search Settings
DEFAULT_SEARCH_LIMIT=100
MAX_SEARCH_LIMIT=500

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=10

# Monitoring (optional)
SENTRY_DSN=

# Admin Tools (optional)
PGADMIN_EMAIL=admin@property-bot.local
PGADMIN_PASSWORD=admin123
GRAFANA_USER=admin
GRAFANA_PASSWORD=admin123
EOF

    print_success ".env.property created"
    echo ""
}

# Build Docker image
build_image() {
    print_header "Building Docker Image"

    print_info "Building property-bot:latest..."
    docker build -f Dockerfile.property -t property-bot:latest .

    print_success "Docker image built successfully"
    echo ""
}

# Start services
start_services() {
    print_header "Starting Services"

    local profile_flags=""

    # Ask which services to start
    read -p "Start with Redis caching? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        profile_flags="$profile_flags --profile redis"
    fi

    read -p "Start with PgAdmin (database admin)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        profile_flags="$profile_flags --profile admin"
    fi

    read -p "Start with monitoring (Prometheus + Grafana)? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        profile_flags="$profile_flags --profile monitoring"
    fi

    print_info "Starting containers..."
    docker-compose -f docker-compose.property.yml --env-file .env.property $profile_flags up -d

    print_success "Services started"
    echo ""
}

# Wait for database
wait_for_database() {
    print_header "Waiting for Database"

    print_info "Waiting for PostgreSQL to be ready..."

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if docker-compose -f docker-compose.property.yml exec -T property-db pg_isready -U property_user -d property_bot &> /dev/null; then
            print_success "Database is ready"
            echo ""
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 1
    done

    print_error "Database did not become ready in time"
    exit 1
}

# Run database migrations
run_migrations() {
    print_header "Running Database Migrations"

    print_info "Applying database schema..."
    docker-compose -f docker-compose.property.yml exec -T property-bot alembic upgrade head

    print_success "Migrations completed"
    echo ""
}

# Load sample data
load_sample_data() {
    print_header "Sample Data"

    read -p "Load sample property data for testing? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Loading sample properties..."
        docker-compose -f docker-compose.property.yml exec -T property-bot python scripts/load_sample_properties.py --count 100
        print_success "Sample data loaded (100 properties)"
    else
        print_info "Skipping sample data"
    fi

    echo ""
}

# Run tests
run_tests() {
    print_header "Running Tests"

    read -p "Run integration tests? (y/N): " -n 1 -r
    echo

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Running tests..."
        docker-compose -f docker-compose.property.yml exec -T property-bot pytest tests/test_property_stage2_integration.py -v
        print_success "Tests completed"
    else
        print_info "Skipping tests"
    fi

    echo ""
}

# Health check
health_check() {
    print_header "Health Check"

    print_info "Checking service health..."

    local max_attempts=10
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if curl -f http://localhost:8001/health &> /dev/null; then
            print_success "Application is healthy"
            echo ""
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    print_warning "Health check did not pass (application may still be starting)"
    echo ""
}

# Display info
display_info() {
    print_header "Deployment Complete!"

    echo -e "${GREEN}Property Search Bot is now running!${NC}"
    echo ""
    echo "Service URLs:"
    echo "  • Application API:  http://localhost:8001"
    echo "  • Health Check:     http://localhost:8001/health"
    echo "  • API Docs:         http://localhost:8001/docs"
    echo ""

    if docker-compose -f docker-compose.property.yml ps | grep -q "property-bot-pgadmin"; then
        echo "  • PgAdmin:          http://localhost:5051"
    fi

    if docker-compose -f docker-compose.property.yml ps | grep -q "property-bot-prometheus"; then
        echo "  • Prometheus:       http://localhost:9091"
        echo "  • Grafana:          http://localhost:3001"
    fi

    echo ""
    echo "Useful commands:"
    echo "  • View logs:        docker-compose -f docker-compose.property.yml logs -f property-bot"
    echo "  • Stop services:    docker-compose -f docker-compose.property.yml down"
    echo "  • Restart:          docker-compose -f docker-compose.property.yml restart property-bot"
    echo "  • Run tests:        docker-compose -f docker-compose.property.yml exec property-bot pytest -v"
    echo ""
    echo "Documentation:"
    echo "  • Deployment Guide: PROPERTY_BOT_DEPLOYMENT.md"
    echo "  • API Guide:        PROPERTY_BOT_API_GUIDE.md"
    echo "  • Full Summary:     PROPERTY_BOT_FINAL_SUMMARY.md"
    echo ""
}

# Main deployment flow
main() {
    clear

    print_header "Property Search Bot Deployment"
    echo -e "${BLUE}Автоматическое развертывание${NC}"
    echo ""

    # Check requirements
    check_requirements

    # Create environment file
    create_env_file

    # Build Docker image
    build_image

    # Start services
    start_services

    # Wait for database
    wait_for_database

    # Run migrations
    run_migrations

    # Load sample data (optional)
    load_sample_data

    # Run tests (optional)
    run_tests

    # Health check
    health_check

    # Display info
    display_info
}

# Handle script arguments
case "${1:-}" in
    "")
        main
        ;;
    "stop")
        print_info "Stopping Property Bot services..."
        docker-compose -f docker-compose.property.yml down
        print_success "Services stopped"
        ;;
    "restart")
        print_info "Restarting Property Bot services..."
        docker-compose -f docker-compose.property.yml restart
        print_success "Services restarted"
        ;;
    "logs")
        docker-compose -f docker-compose.property.yml logs -f property-bot
        ;;
    "status")
        docker-compose -f docker-compose.property.yml ps
        ;;
    "test")
        print_info "Running tests..."
        docker-compose -f docker-compose.property.yml exec property-bot pytest tests/ -v
        ;;
    "clean")
        print_warning "This will remove all containers, volumes, and data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker-compose -f docker-compose.property.yml down -v
            docker rmi property-bot:latest 2>/dev/null || true
            rm -f .env.property
            print_success "Cleaned up"
        fi
        ;;
    "help"|"-h"|"--help")
        echo "Property Bot Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  (none)    - Run full deployment"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart services"
        echo "  logs      - View application logs"
        echo "  status    - Show services status"
        echo "  test      - Run tests"
        echo "  clean     - Remove all containers and data (DESTRUCTIVE)"
        echo "  help      - Show this help message"
        echo ""
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac
