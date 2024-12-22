#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}1. Staging changes...${NC}"
git add .

echo -e "${GREEN}2. Committing changes...${NC}"
git commit -m "$1"

echo -e "${GREEN}3. Pushing to remote...${NC}"
git push origin main

echo -e "${GREEN}4. Killing existing server processes...${NC}"
pkill -f "python run.py"

echo -e "${GREEN}5. Checking for processes on port 5003...${NC}"
PIDS=$(lsof -t -i:5003)
if [ ! -z "$PIDS" ]; then
    echo -e "${GREEN}Killing processes on port 5003...${NC}"
    kill -9 $PIDS
fi

echo -e "${GREEN}6. Starting server...${NC}"
source venv/bin/activate
python run.py &

echo -e "${GREEN}Done! Server is starting up.${NC}"
echo -e "Access the app at: http://127.0.0.1:5003/"
