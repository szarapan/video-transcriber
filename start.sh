#!/bin/bash
# Uruchamia aplikację Streamlit (aktywuje .venv, startuje app.py).
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

source .venv/bin/activate
streamlit run app.py
