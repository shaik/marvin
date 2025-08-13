#!/usr/bin/env bash
set -euo pipefail

# Start the Expo dev server for the mobile app
# - Ensures Node deps are installed
# - Ensures app/.env exists (copies from ../env.example or app/env.example if missing)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$SCRIPT_DIR/app"

cd "$APP_DIR"

# Ensure .env exists
if [ ! -f ".env" ]; then
  if [ -f "../env.example" ]; then
    cp ../env.example .env
    echo "Created app/.env from ../env.example. Update HEROKU_URL and API_AUTH_KEY as needed."
  elif [ -f "env.example" ]; then
    cp env.example .env
    echo "Created app/.env from app/env.example. Update HEROKU_URL and API_AUTH_KEY as needed."
  else
    echo "Warning: No .env found. Create app/.env with HEROKU_URL and optional API_AUTH_KEY." >&2
  fi
fi

# Install Node dependencies if missing
if [ ! -d "node_modules" ]; then
  npm install
fi

# Ensure dotenv is available (used by app.config.js)
if [ ! -d "node_modules/dotenv" ]; then
  npm i -D dotenv
fi

# Launch Expo
exec npx expo start


