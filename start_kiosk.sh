#!/bin/bash

echo "==== KIOSK STARTUP ===="

# Kill anything running on port 5000
echo "[INFO] Killing processes on port 5000..."
sudo fuser -k 5000/tcp || true
sleep 1

# Start backend (bridge.py)
echo "[INFO] Starting backend..."
cd /opt/kiosk || exit 1
/usr/bin/python3 bridge.py > /tmp/bridge.log 2>&1 &

# Wait for backend to become available
echo "[INFO] Waiting for backend..."
for i in {1..20}; do
    if curl -s http://localhost:5000/api/health >/dev/null; then
        echo "[OK] Backend is running"
        break
    fi
    sleep 1
done

# Final check
if ! curl -s http://localhost:5000/api/health >/dev/null; then
    echo "[ERROR] Backend failed to start"
    exit 1
fi

# Launch Chromium in kiosk mode
echo "[INFO] Starting kiosk browser..."
chromium-browser \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --disable-features=TranslateUI \
  --kiosk \
  --incognito \
  --no-first-run \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  http://localhost:5000

