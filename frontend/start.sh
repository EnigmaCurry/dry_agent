#!/bin/sh
set -e

if [ "$DEPLOYMENT" = "development" ]; then
  echo "[start.sh] Starting in development mode..."

  # Install deps (ensure volumes don't wipe them out)
  cd /app/frontend
  npm install

  # Start Vite in background
  echo "[start.sh] Starting Vite dev server..."
  nohup npm run dev -- --host 127.0.0.1 --port 5173 > /var/log/vite.log 2>&1 &

  sleep 1
else
  echo "[start.sh] Starting in production mode..."
fi

echo "[start.sh] Starting nginx..."
exec nginx -g 'daemon off;'
