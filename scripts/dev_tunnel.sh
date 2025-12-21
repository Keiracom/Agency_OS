#!/bin/bash
# FILE: scripts/dev_tunnel.sh
# PURPOSE: ngrok tunnel for local webhook testing
# PHASE: 1 (Foundation + DevOps)
# TASK: DEV-003
# DEPENDENCIES: ngrok CLI installed
# RULES APPLIED:
#   - Rule 1: Follow blueprint exactly
#   - Rule 20: Webhook-first architecture

set -e

# === Configuration ===
API_PORT="${API_PORT:-8000}"
NGROK_CONFIG="${NGROK_CONFIG:-}"
WEBHOOK_UPDATE_SCRIPT="scripts/update_webhook_urls.py"

# === Colors for output ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Agency OS Dev Tunnel ===${NC}"

# === Check ngrok is installed ===
if ! command -v ngrok &> /dev/null; then
    echo -e "${RED}Error: ngrok is not installed${NC}"
    echo "Install ngrok: https://ngrok.com/download"
    exit 1
fi

# === Check if API is running ===
check_api() {
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:${API_PORT}/health" 2>/dev/null || echo "000"
}

API_STATUS=$(check_api)
if [ "$API_STATUS" != "200" ]; then
    echo -e "${YELLOW}Warning: API not responding on port ${API_PORT}${NC}"
    echo "Make sure docker-compose is running: docker-compose up -d"
fi

# === Start ngrok tunnel ===
echo -e "${GREEN}Starting ngrok tunnel on port ${API_PORT}...${NC}"

# Run ngrok in background and capture URL
ngrok http ${API_PORT} --log=stdout > /tmp/ngrok.log 2>&1 &
NGROK_PID=$!

# Wait for ngrok to start
sleep 3

# Get the public URL from ngrok API
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; tunnels=json.load(sys.stdin)['tunnels']; print(next((t['public_url'] for t in tunnels if t['proto']=='https'), ''))" 2>/dev/null || echo "")

if [ -z "$NGROK_URL" ]; then
    echo -e "${RED}Error: Could not get ngrok URL${NC}"
    echo "Check ngrok logs: cat /tmp/ngrok.log"
    kill $NGROK_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}Tunnel active: ${NGROK_URL}${NC}"
echo ""

# === Update webhook URLs ===
if [ -f "$WEBHOOK_UPDATE_SCRIPT" ]; then
    echo -e "${YELLOW}Updating webhook URLs in external services...${NC}"
    python3 "$WEBHOOK_UPDATE_SCRIPT" "$NGROK_URL"
    echo -e "${GREEN}Webhook URLs updated!${NC}"
else
    echo -e "${YELLOW}Webhook update script not found. Manual update required.${NC}"
    echo "Webhook endpoints:"
    echo "  Postmark inbound: ${NGROK_URL}/webhooks/postmark"
    echo "  Twilio SMS:       ${NGROK_URL}/webhooks/twilio/sms"
    echo "  Twilio Voice:     ${NGROK_URL}/webhooks/twilio/voice"
fi

echo ""
echo -e "${GREEN}Press Ctrl+C to stop the tunnel${NC}"

# === Cleanup on exit ===
cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping ngrok tunnel...${NC}"
    kill $NGROK_PID 2>/dev/null
    echo -e "${GREEN}Tunnel stopped.${NC}"
}

trap cleanup EXIT

# Keep script running
wait $NGROK_PID

# === VERIFICATION CHECKLIST ===
# [x] Contract comment at top
# [x] ngrok for webhook testing (as specified)
# [x] Checks API health before tunneling
# [x] Captures public URL
# [x] Triggers webhook URL updater script
# [x] Clean exit handling
# [x] No hardcoded credentials
