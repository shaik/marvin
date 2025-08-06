#!/bin/bash

# pack.sh - Collect all source and config files for AI analysis
# This script creates sources.txt containing all relevant project files

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Output file
OUTPUT_FILE="sources.txt"

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Clear the output file
echo "# Marvin Memory Assistant - Complete Source Code" > "$OUTPUT_FILE"
echo "# Generated on: $(date)" >> "$OUTPUT_FILE"
echo "# This file contains all source and configuration files for AI analysis" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

print_info "Starting source file collection..."

# Function to add a file to the output
add_file() {
    local file_path="$1"
    local full_path="$(pwd)/$file_path"
    
    if [ -f "$file_path" ]; then
        echo "=== FILE: $file_path ===" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        cat "$file_path" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        print_info "Added: $file_path"
    else
        print_warning "File not found: $file_path"
    fi
}

# Function to add files matching a pattern
add_files_pattern() {
    local pattern="$1"
    local description="$2"
    
    print_info "Adding $description..."
    
    # Use find to get files matching the pattern
    find . -name "$pattern" -type f | while read -r file; do
        # Remove the ./ prefix
        file="${file#./}"
        
        # Skip files in excluded directories
        if [[ "$file" =~ ^(node_modules|\.git|__pycache__|\.pytest_cache|build|dist|\.expo|\.vscode|\.idea)/ ]]; then
            continue
        fi
        
        # Skip generated/compiled files
        if [[ "$file" =~ \.(pyc|pyo|log|tmp|cache|db)$ ]]; then
            continue
        fi
        
        add_file "$file"
    done
}

print_info "=== Root Configuration Files ==="

# Root configuration files
add_file "marvin.cursor.yaml"
add_file "deploy.sh"
add_file "pack.sh"
add_file ".gitignore"
add_file "Procfile"
add_file "requirements.txt"

print_info "=== Backend Source Files ==="

# Python source files in agent/
add_files_pattern "*.py" "Python source files"

# Configuration files in agent/
add_file "agent/config.py"
add_file "agent/__init__.py"

print_info "=== API Module Files ==="

# API module files
add_files_pattern "agent/api/*.py" "API module files"

print_info "=== Mobile App Files ==="

# React Native app files
add_file "app/package.json"
add_file "app/app.json"
add_file "app/babel.config.js"
add_file "app/metro.config.js"
add_file "app/App.js"
add_file "app/api.js"
add_file "app/README.md"
add_file "app/env.example"

print_info "=== Documentation Files ==="

# Documentation and config files
add_files_pattern "*.md" "Markdown documentation"
add_files_pattern "*.yaml" "YAML configuration"
add_files_pattern "*.yml" "YAML configuration"
add_files_pattern "*.json" "JSON configuration (excluding node_modules)"

print_info "=== Additional Configuration Files ==="

# Additional config files that might exist
add_files_pattern "*.toml" "TOML configuration"
add_files_pattern "*.ini" "INI configuration"
add_files_pattern "*.conf" "Configuration files"
add_files_pattern "*.env.example" "Environment examples"
add_files_pattern "Dockerfile" "Docker files"
add_files_pattern "docker-compose*.yml" "Docker Compose files"

# Add any shell scripts (but exclude this one to avoid recursion)
find . -name "*.sh" -type f | while read -r file; do
    file="${file#./}"
    
    # Skip this script and files in excluded directories
    if [[ "$file" == "pack.sh" ]] || [[ "$file" =~ ^(node_modules|\.git)/ ]]; then
        continue
    fi
    
    add_file "$file"
done

# Count total lines and files
total_lines=$(wc -l < "$OUTPUT_FILE")
total_files=$(grep -c "=== FILE:" "$OUTPUT_FILE" || echo "0")

print_success "Source collection completed!"
echo ""
print_info "Output file: $OUTPUT_FILE"
print_info "Total files collected: $total_files"
print_info "Total lines: $total_lines"
echo ""

# Display file size
file_size=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
print_info "File size: $file_size"

# Show a preview of what was collected
print_info "File structure collected:"
grep "=== FILE:" "$OUTPUT_FILE" | head -20 | sed 's/=== FILE: \(.*\) ===/  - \1/'

if [ "$total_files" -gt 20 ]; then
    print_info "... and $(($total_files - 20)) more files"
fi

echo ""
print_success "✓ All source files have been packed into $OUTPUT_FILE"
print_info "You can now upload this file to AI engines for analysis"

# Provide usage suggestions
echo ""
print_info "Usage suggestions:"
echo "  - Upload to ChatGPT, Claude, or other AI platforms"
echo "  - Use for code review and analysis"
echo "  - Share with team members for project overview"
echo "  - Keep as project snapshot/backup"