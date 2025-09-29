#!/usr/bin/env bash
set -euo pipefail

python3 -m venv .venv
echo "Created .venv"
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
echo "Virtualenv ready. Activate with: source .venv/bin/activate"
