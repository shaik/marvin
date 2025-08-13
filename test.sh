#!/usr/bin/env bash
set -euo pipefail

# Ensure project virtualenv exists and has deps
if [ ! -x "venv/bin/pytest" ]; then
  python3 -m venv venv
  ./venv/bin/pip install -r requirements.txt
fi

# Activate venv and run tests
source venv/bin/activate
exec pytest tests/ -v --tb=short -W ignore::DeprecationWarning