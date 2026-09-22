#!/usr/bin/env bash
# Render build script — runs on every deploy

set -o errexit  # Exit on error

echo "==> Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Seeding database (creates tables + default data)..."
python seed.py

echo "==> Build complete!"
