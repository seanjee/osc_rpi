#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

export PYTHONPATH=src
exec .venv/bin/python -m rpiosc.app
