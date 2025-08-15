#!/bin/bash

# pack.sh - Collect all source and config text files for AI analysis
# Respects .gitignore strictly and excludes binaries/assets regardless of ignore rules

set -euo pipefail

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

OUTPUT_FILE="sources.txt"
MAX_SIZE_BYTES=$((2 * 1024 * 1024)) # skip files >2MB just in case

print_info() {
	echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
	echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
	echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Ensure we're in a git repo
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
	echo "This script must be run inside a Git repository." >&2
	exit 1
fi

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

# Header
{
	echo "# Marvin Memory Assistant - Source Snapshot"
	echo "# Generated on: $(date -u +'%Y-%m-%dT%H:%M:%SZ')"
	echo "# Only files NOT ignored by .gitignore and detected as text are included"
	echo
} > "$OUTPUT_FILE"

print_info "Collecting files (respecting .gitignore)..."

# We'll stream files directly from git ls-files to avoid using bash 4+ features
added=0

is_text_file() {
	local f="$1"
	# Use file(1) to detect MIME; accept text/* and common textual application types
	local mime
	mime=$(file -b --mime-type -- "$f" 2>/dev/null || echo application/octet-stream)
	case "$mime" in
		text/*) return 0 ;;
		application/json) return 0 ;;
		application/xml) return 0 ;;
		application/x-sh|application/x-shellscript) return 0 ;;
		application/x-yaml|application/yaml) return 0 ;;
		*) return 1 ;;
	esac
}

should_always_skip() {
    local p="$1"
    case "$p" in
        app/node_modules/*|node_modules/*) return 0 ;;
        app/assets/*|assets/*|images/*) return 0 ;;
        *.png|*.jpg|*.jpeg|*.gif|*.webp|*.svg|*.ico|*.pdf|*.ttf|*.otf|*.woff|*.woff2) return 0 ;;
    esac
    return 1
}

# Stream NUL-separated paths and process one by one
git ls-files -z -co --exclude-standard | while IFS= read -r -d '' rel; do
    # Normalize path
    abs=$(python3 -c 'import os,sys;print(os.path.abspath(sys.argv[1]))' "$rel")

    # Safety skips
    if should_always_skip "$rel"; then continue; fi
    if [ ! -f "$rel" ]; then continue; fi
    # Size guard (macOS stat -f%z, Linux stat -c%s fallback)
    size=$(stat -f%z "$rel" 2>/dev/null || stat -c%s "$rel" 2>/dev/null || echo 0)
    if [ "$size" -gt $MAX_SIZE_BYTES ]; then continue; fi
    # MIME/type guard
    if ! is_text_file "$rel"; then continue; fi

    # Append
    echo "=== FILE: $abs ===" >> "$OUTPUT_FILE"
    echo >> "$OUTPUT_FILE"
    cat -- "$rel" >> "$OUTPUT_FILE"
    echo >> "$OUTPUT_FILE"
    echo >> "$OUTPUT_FILE"
    added=$((added+1))
done

print_success "Source collection completed"
print_info "Output file: $OUTPUT_FILE"
print_info "Total files collected: $added"

# Preview
print_info "Preview:"
grep -E "^=== FILE: " "$OUTPUT_FILE" | head -20 | sed 's/^=== FILE: /  - /; s/ ===$//' || true