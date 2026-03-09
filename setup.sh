#!/usr/bin/env bash
set -e

echo "==> Activating/creating virtual environment"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "==> Installing dependencies"
pip install -r requirements.txt

echo "==> Ensuring data directories exist"
mkdir -p data/raw
mkdir -p data/processed

echo "==> Removing old local database"
rm -f data/processed/local.db

echo "==> Rebuilding model artifact"
python scripts_make_dummy_model.py

echo "==> Starting FastAPI server"
uvicorn src.api.app:app --reload --port 8000
