#!/usr/bin/env bash
# Entry point for the Incident Memory Engine development stack on macOS / Linux.
set -euo pipefail
cd "$(dirname "$0")"

if [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
    PY="python3"
else
    echo "Python 3.11+ was not found. Install it and try again." >&2
    exit 1
fi

exec "$PY" start.py "$@"
