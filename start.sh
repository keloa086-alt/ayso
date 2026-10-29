#!/usr/bin/env bash
# يشتغل على Render/Railway/Enzonic — يأخذ $PORT تلقائياً
PORT="${PORT:-10000}"
echo "Ayso → 0.0.0.0:$PORT"
PY=$(command -v python3 || command -v python)
exec "$PY" -m uvicorn app:app --host 0.0.0.0 --port "$PORT" \
     --proxy-headers --forwarded-allow-ips='*'
