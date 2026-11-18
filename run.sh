#!/usr/bin/env bash
# Run main.py inside a virtualenv. Automatically creates the venv and installs dependencies if needed.
# Usage:  ./run.sh [token]      (arguments are passed straight through to main.py)
# Change Python:  PYTHON=python3.12 ./run.sh
set -euo pipefail

# Always run from the directory containing run.sh (.token and agent.json are looked up relative to it)
cd "$(dirname "${BASH_SOURCE[0]}")"

VENV_DIR=".venv"
PYTHON="${PYTHON:-python3}"
REQ="requirements.txt"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "[run.sh] '$PYTHON' not found. Install Python 3 or set the PYTHON variable." >&2
    exit 1
fi

# Create the venv on first run
if [ ! -d "$VENV_DIR" ]; then
    echo "[run.sh] Creating virtualenv in $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Linux/macOS use bin/, Git Bash on Windows uses Scripts/
if [ -x "$VENV_DIR/bin/python" ]; then
    VENV_PY="$VENV_DIR/bin/python"
elif [ -x "$VENV_DIR/Scripts/python" ]; then
    VENV_PY="$VENV_DIR/Scripts/python"
else
    echo "[run.sh] venv is broken. Delete the $VENV_DIR directory and run again." >&2
    exit 1
fi

# Reinstall dependencies only when requirements.txt changes
if command -v sha256sum >/dev/null 2>&1; then
    CURRENT_HASH="$(sha256sum "$REQ" | cut -d' ' -f1)"
else
    CURRENT_HASH="$(shasum -a 256 "$REQ" | cut -d' ' -f1)"
fi
STAMP="$VENV_DIR/.requirements.sha256"

if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$CURRENT_HASH" ]; then
    echo "[run.sh] Installing dependencies from $REQ ..."
    "$VENV_PY" -m pip install --quiet --disable-pip-version-check -r "$REQ"
    echo "$CURRENT_HASH" > "$STAMP"
fi

exec "$VENV_PY" main.py "$@"
