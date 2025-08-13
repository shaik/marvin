#!/usr/bin/env bash
set -euo pipefail

# Use project virtualenv if available; create if missing
if [ ! -x "venv/bin/uvicorn" ]; then
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt
fi

# Activate venv and start the server
source venv/bin/activate
exec uvicorn agent.main:app --host 0.0.0.0 --port "${PORT:-8000}" --reload --reload-dir agent