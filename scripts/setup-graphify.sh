#!/usr/bin/env bash
# Instalación local, reproducible y sin credenciales para Linux/Codex Cloud.
# Uso: bash scripts/setup-graphify.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! "$PYTHON_BIN" -c 'import sys; assert sys.version_info >= (3, 11)' 2>/dev/null; then
  echo "Se necesita Python 3.11 o posterior." >&2
  exit 1
fi
if [[ ! -x .graphify-venv/bin/python ]]; then
  "$PYTHON_BIN" -m venv .graphify-venv
fi
.graphify-venv/bin/python -m pip install --disable-pip-version-check graphifyy
.graphify-venv/bin/graphify extract . --code-only
echo "Grafo generado: graphify-out/graph.json"
echo "Consultar con: .graphify-venv/bin/graphify query 'scripts RetroBat' --budget 1000 --depth 2"
