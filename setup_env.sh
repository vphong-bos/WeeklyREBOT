#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_ROOT"

echo "[WeeklyREBOT] Project root: $PROJECT_ROOT"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[WeeklyREBOT] Error: $PYTHON_BIN not found. Please install Python 3.10+ first."
  exit 1
fi

echo "[WeeklyREBOT] Using Python: $($PYTHON_BIN --version)"

if [ ! -d "$VENV_DIR" ]; then
  echo "[WeeklyREBOT] Creating virtual environment at .venv"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
else
  echo "[WeeklyREBOT] Virtual environment already exists at .venv"
fi

source "$VENV_DIR/bin/activate"

echo "[WeeklyREBOT] Upgrading pip"
python -m pip install --upgrade pip

if [ -f "$PROJECT_ROOT/requirements.txt" ]; then
  echo "[WeeklyREBOT] Installing requirements.txt"
  pip install -r "$PROJECT_ROOT/requirements.txt"
else
  echo "[WeeklyREBOT] Warning: requirements.txt not found, skipping dependency install"
fi

mkdir -p \
  "$PROJECT_ROOT/data/raw" \
  "$PROJECT_ROOT/data/processed" \
  "$PROJECT_ROOT/data/indexes"

touch \
  "$PROJECT_ROOT/data/raw/.gitkeep" \
  "$PROJECT_ROOT/data/processed/.gitkeep" \
  "$PROJECT_ROOT/data/indexes/.gitkeep"

if [ ! -f "$PROJECT_ROOT/.env" ]; then
  if [ -f "$PROJECT_ROOT/.env.example" ]; then
    echo "[WeeklyREBOT] Creating .env from .env.example"
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
  else
    echo "[WeeklyREBOT] Creating empty .env"
    touch "$PROJECT_ROOT/.env"
  fi
else
  echo "[WeeklyREBOT] .env already exists, keeping current file"
fi

echo ""
echo "[WeeklyREBOT] Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit .env with your Jira credentials"
echo "  2. Activate environment: source .venv/bin/activate"
echo "  3. Run report: python scripts/generate_weekly_report.py --start 2026-05-04 --end 2026-05-10"