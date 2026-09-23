#!/usr/bin/env bash
# Script para executar a suíte de testes do CLP Siemens S7-1200
set -e
cd "$(dirname "$0")"

if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

python3 test_demo_visual.py "$@"
