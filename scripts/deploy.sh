#!/bin/bash

# AI Development Playground Deployment Script
# This script helps you deploy the platform to various environments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
    
    print_status "Docker is available"
}

# Check if Docker Compose is installed
check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker Compose is available"
}

# Setup environment file
setup_env() {
    if [ ! -f .env ]; then
        print_status "Creating .env file from template..."
        cp env.example .env
        print_warning "Please edit .env file with your configuration before continuing"
        print_warning "Required variables: AUTH_PASSWORD, GITHUB_TOKEN, GITHUB_USERNAME"
        exit 1
    else
        print_status ".env file already exists"
    fi
}

# Build and start services
deploy_local() {
    print_status "Building and starting services..."
    docker-compose up --build -d
    
    print_status "Waiting for services to start..."
    sleep 10
    
    # Check if services are running
    if docker-compose ps | grep -q "Up"; then
        print_status "Services are running!"
        print_status "Dashboard: http://91.99.196.35:3000"
        print_status "API: http://91.99.196.35:8000"
        print_status "API Docs: http://91.99.196.35:8000/docs"
    else
        print_error "Some services failed to start. Check logs with: docker-compose logs"
        exit 1
    fi
}

# Stop services
stop_services() {
    print_status "Stopping services..."
    docker-compose down
    print_status "Services stopped"
}

# Show logs
show_logs() {
    print_status "Showing logs..."
    docker-compose logs -f
}

# Clean up everything
cleanup() {
    print_status "Cleaning up..."
    docker-compose down -v
    docker system prune -f
    print_status "Cleanup complete"
}

# Main script logic
case "${1:-deploy}" in
    "deploy"|"start")
        check_docker
        check_docker_compose
        setup_env
        deploy_local
        ;;
    "stop")
        stop_services
        ;;
    "restart")
        stop_services
        deploy_local
        ;;
    "logs")
        show_logs
        ;;
    "cleanup")
        cleanup
        ;;
    "help")
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  deploy, start  - Build and start all services"
        echo "  stop          - Stop all services"
        echo "  restart       - Restart all services"
        echo "  logs          - Show service logs"
        echo "  cleanup       - Stop services and clean up volumes"
        echo "  help          - Show this help message"
        ;;
    *)
        print_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac 