#!/bin/bash

# Test PlanProof via Dev Tunnel
# Usage: ./test-tunnel-deployment.sh <your-tunnel-url>

TUNNEL_URL=${1:-"https://gc4g9fbj-3000.inc1.devtunnels.ms"}

echo "=================================="
echo "Testing PlanProof via Dev Tunnel"
echo "=================================="
echo "Tunnel URL: $TUNNEL_URL"
echo ""

# Test frontend
echo "Testing Frontend..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "$TUNNEL_URL"

# Try to get the page
echo ""
echo "Fetching login page..."
curl -s -L "$TUNNEL_URL/login" | head -20

echo ""
echo "=================================="
echo "If you see HTML above, your tunnel is working!"
echo "Open in browser: $TUNNEL_URL"
echo "=================================="
