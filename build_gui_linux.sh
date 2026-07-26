#!/usr/bin/env bash
set -euo pipefail

echo "[1/4] Upgrading pip and checking dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install pyinstaller customtkinter requests

echo
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

VERSION_SUFFIX=""
if [ -n "${VNDB_GUI_VERSION:-}" ]; then
  VERSION_SUFFIX="-${VNDB_GUI_VERSION}"
fi
mkdir -p build/pyinstaller
BUNDLE_VERSION="${VNDB_GUI_VERSION:-dev}"
printf '%s\n' "$BUNDLE_VERSION" > build/pyinstaller/version.txt

echo "[2/4] Locating UI dependencies..."
echo "Found customtkinter at: $(python3 -c 'import os, customtkinter; print(os.path.dirname(customtkinter.__file__))' 2>/dev/null || echo 'checking...')"

echo
echo "[3/4] Building VNDB-GUI..."
mkdir -p release build/pyinstaller

pyinstaller --onefile --windowed --clean \
  --name "VNDB-GUI${VERSION_SUFFIX}" \
  --distpath release \
  --workpath build/pyinstaller \
  --specpath build/pyinstaller \
  --paths "$ROOT_DIR/src" \
  --collect-all customtkinter \
  --add-data "$ROOT_DIR/build/pyinstaller/version.txt:." \
  "$ROOT_DIR/src/gui.py"

echo
echo "[4/4] Finalizing build..."
if [ -f "release/VNDB-GUI${VERSION_SUFFIX}" ]; then
  echo "========================================================"
  echo "SUCCESS! Built: release/VNDB-GUI${VERSION_SUFFIX}"
  echo "========================================================"
else
  echo "ERROR: Build failed. Check the logs above."
  exit 1
fi