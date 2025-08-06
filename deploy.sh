#!/bin/bash

# Marvin Memory Service Deployment Script
# This script handles deployment to Heroku with proper checks and configuration

set -e  # Exit immediately if a command exits with a non-zero status

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if required tools are installed
check_dependencies() {
    print_status "Checking required dependencies..."
    
    if ! command -v git &> /dev/null; then
        print_error "git is not installed. Please install git and try again."
        exit 1
    fi
    
    if ! command -v heroku &> /dev/null; then
        print_error "Heroku CLI is not installed. Please install Heroku CLI and try again."
        print_status "Visit: https://devcenter.heroku.com/articles/heroku-cli"
        exit 1
    fi
    
    print_success "All dependencies are available"
}

# Check if git status is clean
check_git_status() {
    print_status "Checking git repository status..."
    
    if [ ! -d ".git" ]; then
        print_error "Not a git repository. Please initialize git first."
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        print_error "Git repository has uncommitted changes. Please commit or stash changes before deploying."
        git status --porcelain
        exit 1
    fi
    
    # Check for untracked files that might be important
    untracked_files=$(git ls-files --others --exclude-standard)
    if [ -n "$untracked_files" ]; then
        print_warning "Found untracked files:"
        echo "$untracked_files"
        read -p "Continue deployment anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deployment cancelled by user"
            exit 1
        fi
    fi
    
    print_success "Git repository is clean"
}

# Check if OPENAI_API_KEY is set
check_openai_key() {
    print_status "Checking OpenAI API key..."
    
    if [ -z "$OPENAI_API_KEY" ]; then
        print_error "OPENAI_API_KEY environment variable is not set."
        print_status "Please set your OpenAI API key:"
        print_status "export OPENAI_API_KEY=your_api_key_here"
        exit 1
    fi
    
    # Basic validation - check if it looks like an OpenAI key
    if [[ ! $OPENAI_API_KEY =~ ^sk-[a-zA-Z0-9] ]]; then
        print_warning "OPENAI_API_KEY doesn't appear to be a valid OpenAI API key (should start with 'sk-')"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Deployment cancelled by user"
            exit 1
        fi
    fi
    
    print_success "OpenAI API key is configured"
}

# Check Heroku authentication
check_heroku_auth() {
    print_status "Checking Heroku authentication..."
    
    if ! heroku auth:whoami &> /dev/null; then
        print_error "Not logged into Heroku. Please run 'heroku login' first."
        exit 1
    fi
    
    local heroku_user=$(heroku auth:whoami 2>/dev/null)
    print_success "Logged into Heroku as: $heroku_user"
}

# Push code to git repository
push_to_git() {
    print_status "Pushing code to git repository..."
    
    # Determine remote to push to
    local git_remote="origin"
    local git_branch="master"
    
    # Check if HEROKU_REMOTE is set for direct Heroku deployment
    if [ -n "$HEROKU_REMOTE" ]; then
        git_remote="$HEROKU_REMOTE"
        print_status "Using Heroku remote: $HEROKU_REMOTE"
    else
        print_status "Using standard git remote: $git_remote"
    fi
    
    # Check if remote exists
    if ! git remote get-url "$git_remote" &> /dev/null; then
        print_error "Git remote '$git_remote' not found."
        print_status "Available remotes:"
        git remote -v
        exit 1
    fi
    
    # Check current branch
    current_branch=$(git rev-parse --abbrev-ref HEAD)
    print_status "Current branch: $current_branch"
    
    # Push to remote
    if git push "$git_remote" "$current_branch:$git_branch"; then
        print_success "Code pushed to $git_remote successfully"
    else
        print_error "Failed to push code to $git_remote"
        exit 1
    fi
}

# Configure Heroku environment variables
configure_heroku() {
    print_status "Configuring Heroku environment variables..."
    
    # Set OpenAI API key
    if heroku config:set OPENAI_API_KEY="$OPENAI_API_KEY"; then
        print_success "OPENAI_API_KEY configured on Heroku"
    else
        print_error "Failed to set OPENAI_API_KEY on Heroku"
        exit 1
    fi
    
    # Set other recommended environment variables
    print_status "Setting additional configuration..."
    
    heroku config:set LOG_LEVEL=INFO || print_warning "Failed to set LOG_LEVEL"
    heroku config:set APP_NAME="Marvin Memory Service" || print_warning "Failed to set APP_NAME"
    
    # Show current config
    print_status "Current Heroku configuration:"
    heroku config
}

# Initialize database on Heroku
initialize_database() {
    print_status "Initializing database on Heroku dyno..."
    
    # Run database initialization
    if heroku run python -c "from agent.memory import init_db; init_db(); print('Database initialized successfully')"; then
        print_success "Database initialized on Heroku"
    else
        print_error "Failed to initialize database on Heroku"
        print_status "You may need to run this manually:"
        print_status "heroku run python -c \"from agent.memory import init_db; init_db()\""
        exit 1
    fi
}

# Test deployment
test_deployment() {
    print_status "Testing deployment..."
    
    # Get the app URL
    app_url=$(heroku info --json | python3 -c "import sys, json; print(json.load(sys.stdin)['app']['web_url'])" 2>/dev/null || echo "")
    
    if [ -n "$app_url" ]; then
        print_status "Application URL: $app_url"
        print_status "Testing health endpoint..."
        
        # Test health endpoint (with timeout)
        if curl -f -s --max-time 30 "${app_url}health" > /dev/null 2>&1; then
            print_success "Health check passed"
            print_status "API Documentation: ${app_url}docs"
        else
            print_warning "Health check failed or timed out"
            print_status "The app might still be starting up. Check logs with: heroku logs --tail"
        fi
    else
        print_warning "Could not determine app URL"
    fi
}

# Main deployment function
main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Marvin Memory Service Deploy  ${NC}"
    echo -e "${BLUE}================================${NC}"
    echo
    
    # Run all checks and deployment steps
    check_dependencies
    check_git_status
    check_openai_key
    check_heroku_auth
    
    echo
    print_status "Starting deployment process..."
    echo
    
    push_to_git
    configure_heroku
    initialize_database
    test_deployment
    
    echo
    print_success "Deployment completed successfully!"
    echo
    print_status "Next steps:"
    print_status "1. Check logs: heroku logs --tail"
    print_status "2. Visit your app: heroku open"
    print_status "3. View API docs: heroku open --path=/docs"
    echo
}

# Show help
show_help() {
    echo "Marvin Memory Service Deployment Script"
    echo
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -t, --test     Run deployment tests only"
    echo
    echo "Environment Variables:"
    echo "  OPENAI_API_KEY   Your OpenAI API key (required)"
    echo "  HEROKU_REMOTE    Heroku git remote name (optional, defaults to 'origin')"
    echo
    echo "Examples:"
    echo "  export OPENAI_API_KEY=sk-your-key-here"
    echo "  ./deploy.sh"
    echo
    echo "  HEROKU_REMOTE=heroku ./deploy.sh"
}

# Parse command line arguments
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -t|--test)
        check_dependencies
        check_heroku_auth
        test_deployment
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac