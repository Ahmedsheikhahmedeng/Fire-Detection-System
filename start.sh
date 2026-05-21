#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
BACKEND_DIR="$ROOT_DIR/fire-detection-backend"
FRONTEND_DIR="$ROOT_DIR/bitirmeprojesi_frontend"
BACKEND_PYTHON="$BACKEND_DIR/venv311/bin/python"

if [ ! -x "$BACKEND_PYTHON" ]; then
  BACKEND_PYTHON="$BACKEND_DIR/venv/bin/python"
fi

mkdir -p "$RUN_DIR"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Eksik komut: $1"
    exit 1
  fi
}

port_listening() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

require_command lsof
require_command npm

if [ ! -x "$BACKEND_PYTHON" ]; then
  echo "Backend venv bulunamadi: $BACKEND_DIR/venv311/bin/python veya $BACKEND_DIR/venv/bin/python"
  exit 1
fi

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Frontend bagimliliklari eksik. Once bitirmeprojesi_frontend icinde npm install calistir."
  exit 1
fi

if ! port_listening 5432; then
  echo "PostgreSQL 5432 portunda dinlemiyor. Once veritabanini baslat."
  exit 1
fi

echo "Projeyi baslatiyorum..."

if port_listening 8000; then
  echo "Backend zaten calisiyor: http://127.0.0.1:8000"
else
  (
    cd "$BACKEND_DIR"
    nohup "$BACKEND_PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 \
      >"$RUN_DIR/backend.log" 2>&1 &
    echo $! >"$RUN_DIR/backend.pid"
  )
  echo "Backend baslatildi. Log: $RUN_DIR/backend.log"
fi

if port_listening 5173; then
  echo "Frontend zaten calisiyor: http://localhost:5173"
else
  (
    cd "$FRONTEND_DIR"
    npm run build >"$RUN_DIR/frontend-build.log" 2>&1
    nohup npm run preview -- --host 0.0.0.0 --port 5173 >"$RUN_DIR/frontend.log" 2>&1 &
    echo $! >"$RUN_DIR/frontend.pid"
  )
  echo "Frontend baslatildi. Log: $RUN_DIR/frontend.log"
fi

echo "Frontend: http://localhost:5173"
echo "Backend:  http://127.0.0.1:8000/docs"
