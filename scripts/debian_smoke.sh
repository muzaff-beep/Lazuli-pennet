#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3}"

"$PYTHON" -m compileall -q lazulinet run_gui.py
"$PYTHON" -m pytest
"$PYTHON" -c 'import kivy; print("Kivy", kivy.__version__)'

if command -v xvfb-run >/dev/null 2>&1; then
  xvfb-run -a "$PYTHON" scripts/smoke_gui.py
else
  "$PYTHON" scripts/smoke_gui.py
fi
