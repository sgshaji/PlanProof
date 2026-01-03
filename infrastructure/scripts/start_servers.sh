#!/bin/bash

# PlanProof - Start both Backend and Frontend servers
# This script starts the FastAPI backend and Vite frontend dev servers

echo "========================================="
echo "  Starting PlanProof Servers"
echo "========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Please create .env file with Azure credentials"
    exit 1
fi

# Start Backend
echo -e "${YELLOW}Starting Backend (FastAPI on port 8000)...${NC}"
python run_api.py > /tmp/planproof_backend.log 2>&1 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

# Wait for backend to start
sleep 3

# Check backend health
HEALTH=$(curl -s http://localhost:8000/api/v1/health 2>&1)
if [[ $HEALTH == *"healthy"* ]]; then
    echo -e "${GREEN}✓ Backend started successfully${NC}"
else
    echo -e "${RED}✗ Backend failed to start. Check /tmp/planproof_backend.log${NC}"
    exit 1
fi

# Start Frontend
echo -e "\n${YELLOW}Starting Frontend (Vite on port 3000)...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npx vite --host 0.0.0.0 --port 3000 > /tmp/planproof_frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..
echo "Frontend PID: $FRONTEND_PID"

# Wait for frontend to start
sleep 5

# Check frontend
FRONTEND_CHECK=$(curl -s http://localhost:3000 2>&1)
if [[ $FRONTEND_CHECK == *"<title>"* ]]; then
    echo -e "${GREEN}✓ Frontend started successfully${NC}"
else
    echo -e "${RED}✗ Frontend failed to start. Check /tmp/planproof_frontend.log${NC}"
    exit 1
fi

echo ""
echo "========================================="
echo -e "${GREEN}  All Servers Started Successfully!${NC}"
echo "========================================="
echo ""
echo "📍 Backend API:  http://localhost:8000"
echo "📍 API Docs:     http://localhost:8000/api/docs"
echo "📍 Frontend:     http://localhost:3000"
echo ""
echo "📋 Logs:"
echo "   Backend:  /tmp/planproof_backend.log"
echo "   Frontend: /tmp/planproof_frontend.log"
echo ""
echo "🛑 To stop servers:"
echo "   kill $BACKEND_PID $FRONTEND_PID"
echo ""
echo "💡 The UI should now work without CORS errors!"
echo "   Open http://localhost:3000/new-application to test"
echo ""
