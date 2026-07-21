#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

VENV=".venv"
REQ_HASH_FILE=".requirements.hash"

if [ ! -d "$VENV" ]; then
    python3 -m venv --without-pip "$VENV"
    curl -sS https://bootstrap.pypa.io/get-pip.py | "$VENV/bin/python3"
fi

source "$VENV/bin/activate"

CURRENT_HASH=$(md5sum requirements.txt 2>/dev/null || openssl md5 < requirements.txt)
STORED_HASH=$(cat "$REQ_HASH_FILE" 2>/dev/null || echo "")

if [ "$CURRENT_HASH" != "$STORED_HASH" ]; then
    pip install -q -r requirements.txt
    echo "$CURRENT_HASH" > "$REQ_HASH_FILE"
fi

python onboard.py "$@"
