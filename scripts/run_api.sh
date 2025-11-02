#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
PYTHON_BIN="${PYTHON:-python3}"

if [ ! -d "$VENV_DIR" ]; then
  echo "[setup] Creating virtual environment in $VENV_DIR"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

PIP_BIN="$VENV_DIR/bin/pip"
PY_BIN="$VENV_DIR/bin/python"

if [ ! -x "$PIP_BIN" ]; then
  echo "[error] pip not found in virtual environment"
  exit 1
fi

echo "[setup] Upgrading pip"
"$PIP_BIN" install --upgrade pip > /tmp/vbudget-pip.log

if [ -f "$ROOT_DIR/requirements.txt" ]; then
  echo "[setup] Installing project requirements"
  "$PIP_BIN" install -r "$ROOT_DIR/requirements.txt" >> /tmp/vbudget-pip.log
fi

echo "[run] Starting API at http://127.0.0.1:8000"
exec "$PY_BIN" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
