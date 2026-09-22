#!/usr/bin/env bash
cd "$(dirname "$0")"
export LD_LIBRARY_PATH="$HOME/.local/lib:$LD_LIBRARY_PATH"
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi
python3 simulador.py "$@"
