#!/usr/bin/env bash
set -euo pipefail

if ! command -v buildozer >/dev/null 2>&1; then
  echo "buildozer is required for the Android debug build." >&2
  exit 2
fi

buildozer android debug
