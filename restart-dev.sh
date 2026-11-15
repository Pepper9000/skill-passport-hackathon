#!/bin/bash
# Restart the full local stack after a sandbox run restart.
cd /downloads/skill-passport/backend
pkill -f 'uvicorn app.main'; pkill -f vite; pkill -f cloudflared; sleep 1
setsid nohup .venv/bin/python -m uvicorn app.main:app --port 8000 > /tmp/backend.log 2>&1 < /dev/null &
cd ../frontend
VITE_API_BASE_URL=$(grep -m1 '^BE=' /tmp/tunnel-urls.txt | cut -d= -f2) setsid nohup npm run dev > /tmp/frontend.log 2>&1 < /dev/null &
setsid nohup /tmp/cloudflared tunnel --url http://localhost:5173 --no-autoupdate > /tmp/tunnel.log 2>&1 < /dev/null &
setsid nohup /tmp/cloudflared tunnel --url http://localhost:8000 --no-autoupdate > /tmp/tunnel-be.log 2>&1 < /dev/null &
sleep 12
FE=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/tunnel.log | head -1)
BE=$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' /tmp/tunnel-be.log | head -1)
printf 'FE=%s\nBE=%s\n' "$FE" "$BE" > /tmp/tunnel-urls.txt
echo "frontend: $FE  backend: $BE"
echo "NOTE: update backend/.env FRONTEND_ORIGINS with $FE and restart uvicorn; restart vite with VITE_API_BASE_URL=$BE"
