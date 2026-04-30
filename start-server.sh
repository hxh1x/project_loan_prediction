#!/bin/bash
# Lendmark - Start Backend Server
cd "$(dirname "$0")"

# Install dependencies if missing
python3 -c "import flask" 2>/dev/null || pip3 install flask flask-cors

echo ""
echo "  ╔══════════════════════════════════════╗"
echo "  ║     Lendmark Backend Starting...     ║"
echo "  ╚══════════════════════════════════════╝"
echo ""
echo "  URL:  http://localhost:5001"
echo "  Auth: harixx@gmail.com / harixx"
echo ""

python3 backend/server.py
